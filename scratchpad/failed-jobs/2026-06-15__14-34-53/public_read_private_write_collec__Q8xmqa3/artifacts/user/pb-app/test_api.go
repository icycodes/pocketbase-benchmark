package main

import (
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func ptr(s string) *string { return &s }

func TestAPI() {
	app := pocketbase.New()
	
	collection := core.NewBaseCollection("test")
	collection.ListRule = ptr("")
	collection.ViewRule = ptr("")
	collection.CreateRule = ptr("@request.auth.id != \"\"")
	collection.UpdateRule = ptr("@request.auth.id != \"\"")
	collection.DeleteRule = ptr("@request.auth.id != \"\"")
	
	app.Save(collection)
}
