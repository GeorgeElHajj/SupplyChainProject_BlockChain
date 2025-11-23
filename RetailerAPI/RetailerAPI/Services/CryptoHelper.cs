using System;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Extensions.Logging;

namespace RetailerAPI.Services  // Change namespace per API
{
    public class CryptoHelper
    {
        private readonly string _keysDirectory;
        private readonly string _actorName;
        private readonly ILogger? _logger;

        public CryptoHelper(string actorName, string keysDirectory = "keys", ILogger? logger = null)
        {
            _actorName = actorName;
            _keysDirectory = keysDirectory;
            _logger = logger;
        }

        public string SignTransaction(object transactionData)
        {
            var privateKeyPath = Path.Combine(_keysDirectory, $"{_actorName}_private.pem");
            if (!File.Exists(privateKeyPath))
                throw new FileNotFoundException($"Private key not found for {_actorName}");

            string canonicalJson = CanonicalizeJson(transactionData);

            // LOG what we're signing
            _logger?.LogWarning("🔐 SIGNING JSON: {Json}", canonicalJson);

            var dataBytes = Encoding.UTF8.GetBytes(canonicalJson);
            var privateKeyPem = File.ReadAllText(privateKeyPath);

            using var rsa = RSA.Create();
            rsa.ImportFromPem(privateKeyPem);

            var signature = rsa.SignData(dataBytes, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
            return Convert.ToBase64String(signature);
        }

        private static string CanonicalizeJson(object obj)
        {
            using var doc = JsonDocument.Parse(JsonSerializer.Serialize(obj));
            return SerializeCanonical(doc.RootElement);
        }

        private static string SerializeCanonical(JsonElement element)
        {
            switch (element.ValueKind)
            {
                case JsonValueKind.Object:
                    var props = element.EnumerateObject()
                        .OrderBy(p => p.Name, StringComparer.Ordinal)
                        .Select(p => $"\"{p.Name}\":{SerializeCanonical(p.Value)}");
                    return "{" + string.Join(",", props) + "}";
                case JsonValueKind.Array:
                    var items = element.EnumerateArray().Select(SerializeCanonical);
                    return "[" + string.Join(",", items) + "]";
                case JsonValueKind.String:
                    return JsonSerializer.Serialize(element.GetString());
                case JsonValueKind.Number:
                    return element.GetRawText();
                case JsonValueKind.True:
                case JsonValueKind.False:
                    return element.GetRawText().ToLower();
                case JsonValueKind.Null:
                    return "null";
                default:
                    throw new InvalidOperationException("Unsupported JSON value kind.");
            }
        }

        public string GetPublicKey()
        {
            var publicKeyPath = Path.Combine(_keysDirectory, $"{_actorName}_public.pem");
            if (!File.Exists(publicKeyPath))
                throw new FileNotFoundException($"Public key not found for {_actorName}");

            var publicKeyPem = File.ReadAllBytes(publicKeyPath);
            return Convert.ToBase64String(publicKeyPem);
        }

        public bool KeysExist() =>
            File.Exists(Path.Combine(_keysDirectory, $"{_actorName}_private.pem")) &&
            File.Exists(Path.Combine(_keysDirectory, $"{_actorName}_public.pem"));
    }
}