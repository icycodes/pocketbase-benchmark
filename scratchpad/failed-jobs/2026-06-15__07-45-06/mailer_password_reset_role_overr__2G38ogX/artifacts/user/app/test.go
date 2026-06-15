package main

import (
	"fmt"
	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func init() {
	app := pocketbase.New()
	app.OnMailerRecordPasswordResetSend().Add(func(e *core.MailerRecordEvent) error {
		fmt.Println("Hook invoked!")
		return nil
	})
}
