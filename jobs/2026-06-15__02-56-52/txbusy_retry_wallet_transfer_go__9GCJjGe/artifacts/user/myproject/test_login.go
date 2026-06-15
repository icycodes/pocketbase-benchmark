package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

func main() {
	// 1. Login
	loginBody := map[string]string{
		"identity": "tester@example.com",
		"password": "password123", // Assuming password123 or similar
	}
	b, _ := json.Marshal(loginBody)
	resp, err := http.Post("http://127.0.0.1:8090/api/collections/users/auth-with-password", "application/json", bytes.NewBuffer(b))
	if err != nil {
		fmt.Println("Error:", err)
		return
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	fmt.Println("Login response:", string(body))
}
