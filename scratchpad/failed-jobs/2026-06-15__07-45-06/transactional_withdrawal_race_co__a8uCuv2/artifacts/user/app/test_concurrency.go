package main

import (
    "bytes"
    "fmt"
    "net/http"
    "sync"
)

func main() {
    var wg sync.WaitGroup
    for i := 0; i < 10; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            resp, err := http.Post("http://localhost:8090/api/collections/withdrawals/records", "application/json", bytes.NewBuffer([]byte(`{"wallet_id": "z8kcnuz9i4karqy", "amount": 10}`)))
            if err != nil {
                fmt.Println("Error:", err)
                return
            }
            fmt.Println("Status:", resp.StatusCode)
        }()
    }
    wg.Wait()
}
