using DistributorAPI.DTOs;
using Microsoft.Extensions.Options;
using System.Net.Http.Json;

namespace DistributorAPI.Services
{
    public class BlockchainOptions
    {
        public List<string> NodeUrls { get; set; } = new List<string>
        {
            "http://blockchain1:5000",
            "http://blockchain2:5000",
            "http://blockchain3:5000"
        };
        public int TimeoutSeconds { get; set; } = 10;
        public int MaxRetries { get; set; } = 3;
        public bool EnableCrypto { get; set; } = true;
        public string ActorName { get; set; } = "Distributor_B";
        public int HealthCheckIntervalSeconds { get; set; } = 30;
    }

    public class BlockchainService
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly BlockchainOptions _options;
        private readonly ILogger<BlockchainService> _logger;
        private readonly CryptoHelper? _crypto;

        private int _currentNodeIndex = 0;
        private readonly object _lock = new object();
        private List<bool> _nodeHealthStatus;

        public BlockchainService(
            IHttpClientFactory httpClientFactory,
            IOptions<BlockchainOptions> options,
            ILogger<BlockchainService> logger)
        {
            _httpClientFactory = httpClientFactory;
            _options = options.Value;
            _logger = logger;
            _nodeHealthStatus = Enumerable.Repeat(true, _options.NodeUrls.Count).ToList();

            // Initialize crypto for fallback actor
            if (_options.EnableCrypto)
            {
                try
                {
                    _crypto = new CryptoHelper(_options.ActorName, "keys", _logger);
                    if (!_crypto.KeysExist())
                    {
                        _logger.LogWarning("Crypto keys not found for {Actor}. Run setup_actors.py first!", _options.ActorName);
                        _crypto = null;
                    }
                    else
                    {
                        _logger.LogInformation("Crypto enabled for fallback actor {Actor}", _options.ActorName);
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Failed to initialize crypto");
                    _crypto = null;
                }
            }

            // Start background health check
            _ = Task.Run(BackgroundHealthCheck);
        }

        private async Task BackgroundHealthCheck()
        {
            while (true)
            {
                try
                {
                    await Task.Delay(TimeSpan.FromSeconds(_options.HealthCheckIntervalSeconds));
                    await CheckAllNodesHealth();
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Error in background health check");
                }
            }
        }

        private async Task CheckAllNodesHealth()
        {
            for (int i = 0; i < _options.NodeUrls.Count; i++)
            {
                try
                {
                    var client = _httpClientFactory.CreateClient();
                    client.BaseAddress = new Uri(_options.NodeUrls[i]);
                    client.Timeout = TimeSpan.FromSeconds(5);

                    var response = await client.GetAsync("/status");
                    _nodeHealthStatus[i] = response.IsSuccessStatusCode;

                    if (_nodeHealthStatus[i])
                    {
                        _logger.LogDebug("Node {Index} ({Url}) is healthy", i, _options.NodeUrls[i]);
                    }
                    else
                    {
                        _logger.LogWarning("Node {Index} ({Url}) returned non-success status", i, _options.NodeUrls[i]);
                    }
                }
                catch (Exception ex)
                {
                    _nodeHealthStatus[i] = false;
                    _logger.LogWarning(ex, "Node {Index} ({Url}) health check failed", i, _options.NodeUrls[i]);
                }
            }

            _logger.LogInformation("Node health status: {Status}",
                string.Join(", ", _nodeHealthStatus.Select((h, i) => $"Node{i}={h}")));
        }

        private HttpClient GetNextHealthyNode()
        {
            lock (_lock)
            {
                // Try current node first
                if (_nodeHealthStatus[_currentNodeIndex])
                {
                    var client = CreateHttpClient(_currentNodeIndex);
                    _logger.LogInformation("Using primary node {Index}: {Url}",
                        _currentNodeIndex, _options.NodeUrls[_currentNodeIndex]);
                    return client;
                }

                // Find next healthy node
                for (int attempt = 0; attempt < _options.NodeUrls.Count; attempt++)
                {
                    int nextIndex = (_currentNodeIndex + attempt + 1) % _options.NodeUrls.Count;

                    if (_nodeHealthStatus[nextIndex])
                    {
                        _currentNodeIndex = nextIndex;
                        _logger.LogWarning("Switched to backup node {Index}: {Url}",
                            nextIndex, _options.NodeUrls[nextIndex]);
                        return CreateHttpClient(nextIndex);
                    }
                }

                // No healthy nodes found, use current and let it fail
                _logger.LogError("No healthy nodes available! Using node {Index} anyway", _currentNodeIndex);
                return CreateHttpClient(_currentNodeIndex);
            }
        }

        private HttpClient CreateHttpClient(int nodeIndex)
        {
            var client = _httpClientFactory.CreateClient();
            client.BaseAddress = new Uri(_options.NodeUrls[nodeIndex]);
            client.Timeout = TimeSpan.FromSeconds(_options.TimeoutSeconds);
            return client;
        }

        // ==================== DISTRIBUTOR-SPECIFIC METHODS ====================

        public async Task<bool> ReceiveAsync(ReceiveDTO dto)
        {
            CryptoHelper? cryptoToUse = null;

            if (_options.EnableCrypto)
            {
                try
                {
                    cryptoToUse = new CryptoHelper(dto.DistributorName, "keys", _logger);
                    if (!cryptoToUse.KeysExist())
                    {
                        _logger.LogError("Keys not found for {Actor}", dto.DistributorName);
                        return false;
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Failed to load crypto for {Actor}", dto.DistributorName);
                    return false;
                }
            }

            var payload = new
            {
                batch_id = dto.BatchId,
                action = "received",
                actor = dto.DistributorName,
                metadata = new { from = dto.SupplierName,
                    to = dto.DistributorName
                }
            };

            return await SendTransactionAsync(payload, cryptoToUse);
        }

        public async Task<bool> StoreAsync(StoreDTO dto)
        {
            CryptoHelper? cryptoToUse = null;

            if (_options.EnableCrypto)
            {
                try
                {
                    cryptoToUse = new CryptoHelper(dto.DistributorName, "keys", _logger);
                    if (!cryptoToUse.KeysExist())
                    {
                        _logger.LogError("Keys not found for {Actor}", dto.DistributorName);
                        return false;
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Failed to load crypto for {Actor}", dto.DistributorName);
                    return false;
                }
            }

            var payload = new
            {
                batch_id = dto.BatchId,
                action = "stored",
                actor = dto.DistributorName,
                metadata = new { location = dto.WarehouseLocation }
            };

            return await SendTransactionAsync(payload, cryptoToUse);
        }

        public async Task<bool> DeliverAsync(DeliverDTO dto)
        {
            CryptoHelper? cryptoToUse = null;

            if (_options.EnableCrypto)
            {
                try
                {
                    cryptoToUse = new CryptoHelper(dto.DistributorName, "keys", _logger);
                    if (!cryptoToUse.KeysExist())
                    {
                        _logger.LogError("Keys not found for {Actor}", dto.DistributorName);
                        return false;
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Failed to load crypto for {Actor}", dto.DistributorName);
                    return false;
                }
            }

            var payload = new
            {
                batch_id = dto.BatchId,
                action = "delivered",
                actor = dto.DistributorName,
                metadata = new
                {
                    from = dto.DistributorName,
                    to = dto.RetailerName
                }
            };

            return await SendTransactionAsync(payload, cryptoToUse);
        }

        // ==================== COMMON METHODS ====================

        public async Task<object?> GetHistoryAsync(string batchId)
        {
            for (int nodeAttempt = 0; nodeAttempt < _options.NodeUrls.Count; nodeAttempt++)
            {
                try
                {
                    var client = GetNextHealthyNode();
                    _logger.LogInformation("Fetching history for {BatchId}", batchId);
                    var response = await client.GetAsync($"/history/{batchId}");

                    if (response.IsSuccessStatusCode)
                    {
                        return await response.Content.ReadFromJsonAsync<object>();
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Attempt {Attempt} failed, trying next node", nodeAttempt + 1);
                    lock (_lock)
                    {
                        _nodeHealthStatus[_currentNodeIndex] = false;
                    }
                }
            }

            _logger.LogError("All nodes failed to fetch history");
            return null;
        }

        public async Task<bool> MineBlockAsync()
        {
            // Try to mine on all healthy nodes for consensus
            var mineTasks = new List<Task<bool>>();

            for (int i = 0; i < _options.NodeUrls.Count; i++)
            {
                if (_nodeHealthStatus[i])
                {
                    mineTasks.Add(MineOnNodeAsync(i));
                }
            }

            if (mineTasks.Count == 0)
            {
                _logger.LogError("No healthy nodes available for mining");
                return false;
            }

            var results = await Task.WhenAll(mineTasks);
            return results.Any(r => r);
        }

        private async Task<bool> MineOnNodeAsync(int nodeIndex)
        {
            try
            {
                var client = CreateHttpClient(nodeIndex);
                var response = await client.PostAsync("/mine", null);

                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation("Mining successful on node {Index}", nodeIndex);
                    return true;
                }

                return false;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Mining failed on node {Index}", nodeIndex);
                return false;
            }
        }

        public async Task<bool> HealthCheckAsync()
        {
            return _nodeHealthStatus.Any(h => h);
        }

        private async Task<bool> SendTransactionAsync(object payload, CryptoHelper? cryptoOverride = null)
        {
            var payloadDict = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(
                System.Text.Json.JsonSerializer.Serialize(payload)
            );

            if (payloadDict == null)
            {
                _logger.LogError("Failed to serialize payload");
                return false;
            }

            payloadDict["timestamp"] = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.ffffff");

            // Sign transaction if crypto enabled
            var cryptoToUse = cryptoOverride ?? _crypto;
            if (cryptoToUse != null)
            {
                try
                {
                    var signature = cryptoToUse.SignTransaction(payloadDict);
                    var publicKey = cryptoToUse.GetPublicKey();

                    payloadDict["signature"] = signature;
                    payloadDict["public_key"] = publicKey;

                    var actorName = payloadDict.ContainsKey("actor") ? payloadDict["actor"]?.ToString() : "Unknown";
                    _logger.LogInformation("Transaction signed with {Actor}'s key", actorName);
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Failed to sign transaction");
                    return false;
                }
            }

            // Try all nodes with failover
            for (int nodeAttempt = 0; nodeAttempt < _options.NodeUrls.Count; nodeAttempt++)
            {
                try
                {
                    var client = GetNextHealthyNode();
                    _logger.LogInformation("Sending transaction to node (attempt {Attempt})", nodeAttempt + 1);

                    var response = await client.PostAsJsonAsync("/add-transaction", payloadDict);

                    if (response.IsSuccessStatusCode)
                    {
                        _logger.LogInformation("Transaction sent successfully");
                        return true;
                    }

                    if (response.StatusCode == System.Net.HttpStatusCode.Unauthorized)
                    {
                        _logger.LogError("Transaction rejected: Invalid signature");
                        return false;
                    }

                    if ((int)response.StatusCode >= 400 && (int)response.StatusCode < 500)
                    {
                        var errorContent = await response.Content.ReadAsStringAsync();
                        _logger.LogWarning("Transaction rejected: {Error}", errorContent);
                        return false;
                    }

                    // Server error, try next node
                    lock (_lock)
                    {
                        _nodeHealthStatus[_currentNodeIndex] = false;
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Node attempt {Attempt} failed, trying next node", nodeAttempt + 1);
                    lock (_lock)
                    {
                        _nodeHealthStatus[_currentNodeIndex] = false;
                    }
                }

                await Task.Delay(TimeSpan.FromSeconds(1)); // Brief delay between node attempts
            }

            _logger.LogError("Transaction failed on all nodes");
            return false;
        }
    }
}