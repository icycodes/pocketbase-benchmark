package main

import (
	"fmt"
	"github.com/pocketbase/pocketbase/models/settings"
)

func main() {
	t := settings.EmailTemplate{
		ActionUrl: "http://example.com/{TOKEN}",
	}
	s, b, a := t.Resolve("My App", "http://app.com", "123456")
	fmt.Println(s, b, a)
}
