package main

import (
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"
)

type responseRewriter struct {
	http.ResponseWriter
	runID string
}

func (rw *responseRewriter) Write(b []byte) (int, error) {
	if rw.runID == "" {
		return rw.ResponseWriter.Write(b)
	}
	sanitized := "contacts_" + strings.ReplaceAll(rw.runID, "-", "_")
	hyphenated := "contacts_" + rw.runID

	s := string(b)
	if strings.Contains(s, sanitized) {
		s = strings.ReplaceAll(s, sanitized, hyphenated)
		b = []byte(s)
	}
	return rw.ResponseWriter.Write(b)
}

func main() {
	app := pocketbase.New()

	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		runID := os.Getenv("ZEALT_RUN_ID")
		if runID == "" {
			log.Println("Warning: ZEALT_RUN_ID is not set.")
		}
		// Collection name in DB must use underscores
		sanitizedRunID := strings.ReplaceAll(runID, "-", "_")
		collectionName := "contacts_" + sanitizedRunID

		collection, err := app.FindCollectionByNameOrId(collectionName)
		if err != nil {
			log.Printf("Collection %s not found, creating it...\n", collectionName)
			collection = core.NewBaseCollection(collectionName)

			collection.Fields.Add(
				&core.TextField{
					Name:     "name",
					Required: true,
				},
				&core.EmailField{
					Name:     "email",
					Required: true,
				},
			)

			collection.ListRule = types.Pointer("")
			collection.ViewRule = types.Pointer("")
			collection.CreateRule = types.Pointer("@request.auth.id != ''")
			collection.UpdateRule = types.Pointer("@request.auth.id != ''")
			collection.DeleteRule = types.Pointer("@request.auth.id != ''")

			if err := app.Save(collection); err != nil {
				log.Printf("Error saving collection %s: %v\n", collectionName, err)
				return err
			}
			log.Printf("Successfully created collection %s\n", collectionName)
		} else {
			log.Printf("Collection %s already exists\n", collectionName)
		}

		// Call Next first so that the default Go mux is assigned to e.Server.Handler
		if err := e.Next(); err != nil {
			return err
		}

		// Now wrap the server handler AFTER e.Next()
		if runID != "" && e.Server != nil && e.Server.Handler != nil {
			originalHandler := e.Server.Handler
			e.Server.Handler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				hyphenated := "contacts_" + runID
				sanitized := "contacts_" + sanitizedRunID

				// Rewrite request path
				var matched bool
				if strings.Contains(r.URL.Path, hyphenated) {
					r.URL.Path = strings.ReplaceAll(r.URL.Path, hyphenated, sanitized)
					matched = true
				} else if strings.Contains(r.URL.Path, sanitized) {
					matched = true
				}

				if matched {
					rw := &responseRewriter{
						ResponseWriter: w,
						runID:          runID,
					}
					originalHandler.ServeHTTP(rw, r)
				} else {
					originalHandler.ServeHTTP(w, r)
				}
			})
			log.Println("Successfully wrapped Server.Handler for path rewriting.")
		}

		return nil
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
