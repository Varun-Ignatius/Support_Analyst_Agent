
```

## Query logs


# Basic search
"database connection timeout"

# Filter by severity
"auth failure" --severity ERROR CRITICAL

# Filter by service
"slow response" --service payment-svc

#Filter by layer
"error" --file layer.log --severity ERROR CRITICAL

# Filter by time range
"disk full" --since "2024-01-15 14:00" --until "2024-01-15 16:00"

# More results
"out of memory" --top 20
```


```

