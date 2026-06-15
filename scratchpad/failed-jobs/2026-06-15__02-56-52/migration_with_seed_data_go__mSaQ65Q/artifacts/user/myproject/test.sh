#!/bin/bash
set -e

cd /home/user/myproject
rm -rf pb_data
go build -o app .

echo "Running migrate up..."
./app migrate up

echo "Starting server..."
./app serve --http=0.0.0.0:8090 > /dev/null 2>&1 &
PID=$!
sleep 2

echo "Checking categories..."
curl -s http://localhost:8090/api/collections/categories/records | grep -q '"totalItems":3' || { echo "Categories test failed"; kill $PID; exit 1; }

echo "Checking articles..."
curl -s http://localhost:8090/api/collections/articles/records | grep -q '"totalItems":6' || { echo "Articles test failed"; kill $PID; exit 1; }

kill $PID
sleep 1

echo "Running migrate down 1..."
echo y | ./app migrate down 1

echo "Starting server again..."
./app serve --http=0.0.0.0:8090 > /dev/null 2>&1 &
PID=$!
sleep 2

echo "Checking categories 404..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/collections/categories/records)
if [ "$HTTP_STATUS" -ne 404 ]; then
    echo "Categories 404 test failed, got $HTTP_STATUS"
    kill $PID
    exit 1
fi

echo "Checking articles 404..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8090/api/collections/articles/records)
if [ "$HTTP_STATUS" -ne 404 ]; then
    echo "Articles 404 test failed, got $HTTP_STATUS"
    kill $PID
    exit 1
fi

kill $PID
sleep 1

echo "Running migrate up again..."
./app migrate up

echo "Starting server again..."
./app serve --http=0.0.0.0:8090 > /dev/null 2>&1 &
PID=$!
sleep 2

echo "Checking categories again..."
curl -s http://localhost:8090/api/collections/categories/records | grep -q '"totalItems":3' || { echo "Categories test 2 failed"; kill $PID; exit 1; }

echo "Checking articles again..."
curl -s http://localhost:8090/api/collections/articles/records | grep -q '"totalItems":6' || { echo "Articles test 2 failed"; kill $PID; exit 1; }

kill $PID
echo "All tests passed!"
