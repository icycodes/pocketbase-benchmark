package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"sync"
)

type Wallet struct {
	Id      string  `json:"id"`
	Balance float64 `json:"balance"`
}

type Withdrawal struct {
	Id       string  `json:"id"`
	WalletId string  `json:"wallet_id"`
	Amount   float64 `json:"amount"`
}

func main() {
	baseURL := "http://localhost:8090/api/collections"

	// 1. Create a wallet with 50.0 balance
	walletData := map[string]interface{}{
		"balance": 50.0,
	}
	bodyBytes, _ := json.Marshal(walletData)
	resp, err := http.Post(baseURL+"/wallets/records", "application/json", bytes.NewBuffer(bodyBytes))
	if err != nil {
		fmt.Printf("Failed to create wallet: %v\n", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		respBody, _ := io.ReadAll(resp.Body)
		fmt.Printf("Failed to create wallet. Status: %d, Body: %s\n", resp.StatusCode, respBody)
		return
	}

	var wallet Wallet
	if err := json.NewDecoder(resp.Body).Decode(&wallet); err != nil {
		fmt.Printf("Failed to decode wallet: %v\n", err)
		return
	}
	fmt.Printf("Created wallet with ID: %s, Balance: %.2f\n", wallet.Id, wallet.Balance)

	// 2. Fire 10 concurrent withdrawal requests of 10.0 each
	numRequests := 10
	withdrawalAmount := 10.0

	var wg sync.WaitGroup
	statusCodes := make([]int, numRequests)
	errorMessages := make([]string, numRequests)

	for i := 0; i < numRequests; i++ {
		wg.Add(1)
		go func(index int) {
			defer wg.Done()

			reqData := map[string]interface{}{
				"wallet_id": wallet.Id,
				"amount":    withdrawalAmount,
			}
			reqBytes, _ := json.Marshal(reqData)
			reqResp, err := http.Post(baseURL+"/withdrawals/records", "application/json", bytes.NewBuffer(reqBytes))
			if err != nil {
				statusCodes[index] = -1
				errorMessages[index] = err.Error()
				return
			}
			defer reqResp.Body.Close()

			statusCodes[index] = reqResp.StatusCode
			if reqResp.StatusCode != http.StatusOK && reqResp.StatusCode != http.StatusCreated {
				respBody, _ := io.ReadAll(reqResp.Body)
				errorMessages[index] = string(respBody)
			}
		}(i)
	}

	wg.Wait()

	// 3. Analyze results
	successCount := 0
	failureCount := 0
	badRequestCount := 0

	for i := 0; i < numRequests; i++ {
		code := statusCodes[i]
		if code == http.StatusOK || code == http.StatusCreated {
			successCount++
		} else {
			failureCount++
			if code == http.StatusBadRequest {
				badRequestCount++
			}
			fmt.Printf("Request %d failed with status %d: %s\n", i, code, errorMessages[i])
		}
	}

	fmt.Printf("\n--- Concurrency Test Results ---\n")
	fmt.Printf("Total Requests: %d\n", numRequests)
	fmt.Printf("Successes (200/201): %d\n", successCount)
	fmt.Printf("Failures: %d\n", failureCount)
	fmt.Printf("Bad Requests (400): %d\n", badRequestCount)

	// 4. Fetch final wallet balance
	getResp, err := http.Get(baseURL + "/wallets/records/" + wallet.Id)
	if err != nil {
		fmt.Printf("Failed to fetch wallet: %v\n", err)
		return
	}
	defer getResp.Body.Close()

	var finalWallet Wallet
	if err := json.NewDecoder(getResp.Body).Decode(&finalWallet); err != nil {
		fmt.Printf("Failed to decode final wallet: %v\n", err)
		return
	}
	fmt.Printf("Final Wallet Balance: %.2f\n", finalWallet.Balance)

	// 5. Verification
	if successCount == 5 && failureCount == 5 && finalWallet.Balance == 0.0 {
		fmt.Println("SUCCESS: Exactly 5 requests succeeded, 5 failed, and balance is exactly 0.0!")
	} else {
		fmt.Println("FAILURE: Results do not match the expected 5 successes, 5 failures, or 0.0 balance.")
	}
}
