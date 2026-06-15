package main

import (
	"log"
	"strings"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/plugins/migratecmd"
	"github.com/pocketbase/pocketbase/tools/osutils"

	_ "myproject/migrations"
)

func main() {
	app := pocketbase.New()

	migratecmd.MustRegister(app, app.RootCmd, migratecmd.Config{
		Automigrate: osutils.IsProbablyGoRun(),
	})

	// Register global router middleware to intercept attempts to modify the owner field
	app.OnServe().BindFunc(func(se *core.ServeEvent) error {
		se.Router.BindFunc(func(e *core.RequestEvent) error {
			parts := strings.Split(e.Request.URL.Path, "/")
			if (e.Request.Method == "PATCH" || e.Request.Method == "PUT") &&
				len(parts) >= 6 &&
				parts[1] == "api" &&
				parts[2] == "collections" &&
				parts[3] == "posts" &&
				parts[4] == "records" {

				postID := parts[5]

				// Fetch the post record
				post, err := app.FindRecordById("posts", postID)
				if err == nil && post != nil {
					// Check if the authenticated user is the owner of the post
					if e.Auth != nil && e.Auth.Id == post.GetString("owner") {
						// The user IS the owner of the post.
						// Check if they are attempting to modify the owner field.
						info, err := e.RequestInfo()
						if err == nil && info != nil {
							if _, ok := info.Body["owner"]; ok {
								return e.BadRequestError("The owner field cannot be modified.", nil)
							}
						}
					}
				}
			}

			return e.Next()
		})

		return se.Next()
	})

	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
