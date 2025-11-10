Write-Host "==== 1. Register product ===="
Invoke-WebRequest -Uri "http://localhost:5175/api/supplier/add-product" `
  -Method POST -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"BatchId":"DOCKER_001","ProductName":"Laptops","Quantity":100,"Supplier":"Supplier_A"}'

Write-Host "`n==== 2. Quality check ===="
Invoke-WebRequest -Uri "http://localhost:5175/api/supplier/quality-check" `
  -Method POST -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"BatchId":"DOCKER_001","Result":"passed","Inspector":"QA","SupplierName":"Supplier_A"}'

Write-Host "`n==== 3. Ship to distributor ===="
Invoke-WebRequest -Uri "http://localhost:5175/api/supplier/ship" `
  -Method POST -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"BatchId":"DOCKER_001","DistributorName":"Distributor_B","SupplierName":"Supplier_A"}'

Write-Host "`n==== 4. Mine block (Supplier Node) ===="
Invoke-WebRequest -Uri "http://localhost:5000/mine" -Method POST
Start-Sleep -Seconds 2

Write-Host "`n==== 5. Distributor receives ===="
Invoke-WebRequest -Uri "http://localhost:5137/api/distributor/receive" `
  -Method POST -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"BatchId":"DOCKER_001","SupplierName":"Supplier_A","DistributorName":"Distributor_B"}'

Write-Host "`n==== 6. Store in warehouse ===="
Invoke-WebRequest -Uri "http://localhost:5137/api/distributor/store" `
  -Method POST -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"BatchId":"DOCKER_001","DistributorName":"Distributor_B","WarehouseLocation":"WH7"}'

Write-Host "`n==== 7. Deliver to retailer ===="
Invoke-WebRequest -Uri "http://localhost:5137/api/distributor/deliver" `
  -Method POST -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"BatchId":"DOCKER_001","RetailerName":"Retailer_C","DistributorName":"Distributor_B"}'

Write-Host "`n==== 8. Mine block (Distributor Node) ===="
Invoke-WebRequest -Uri "http://localhost:5001/mine" -Method POST
Start-Sleep -Seconds 2

Write-Host "`n==== 9. Retailer receives ===="
Invoke-WebRequest -Uri "http://localhost:5112/api/retailer/receive" `
  -Method POST -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"BatchId":"DOCKER_001","RetailerName":"Retailer_C","DistributorName":"Distributor_B"}'

Write-Host "`n==== 10. Sell to customer ===="
Invoke-WebRequest -Uri "http://localhost:5112/api/retailer/sold" `
  -Method POST -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"BatchId":"DOCKER_001","RetailerName":"Retailer_C","CustomerName":"John","SaleDate":"2025-11-08"}'

Write-Host "`n==== 11. Mine final block (Retailer Node) ===="
Invoke-WebRequest -Uri "http://localhost:5002/mine" -Method POST
Start-Sleep -Seconds 5

Write-Host "`n==== 12. Get history ===="
Invoke-WebRequest -Uri "http://localhost:5175/api/supplier/history/DOCKER_001" -Method GET

Write-Host "`n==== 13. Verify product ===="
Invoke-WebRequest -Uri "http://localhost:5112/api/retailer/verify/DOCKER_001" -Method GET
