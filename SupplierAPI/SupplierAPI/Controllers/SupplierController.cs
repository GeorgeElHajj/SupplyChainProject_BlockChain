using DistributorAPI.DTOs;
using Microsoft.AspNetCore.Mvc;
using SupplierAPI.DTOs;
using SupplierAPI.Services;

namespace SupplierAPI.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class SupplierController : ControllerBase
    {
        private readonly BlockchainService _blockchain;

        public SupplierController(BlockchainService blockchain)
        {
            _blockchain = blockchain;
        }

        [HttpPost("add-product")]
        public async Task<IActionResult> AddProduct([FromBody] ProductDTO dto)
        {
            var result = await _blockchain.AddProductAsync(dto);
            if (!result)
                return BadRequest("Failed to add product to blockchain.");
            return Ok("Product registered successfully.");
        }

        [HttpPost("quality-check")]
        public async Task<IActionResult> QualityCheck([FromBody] QualityCheckDTO dto)
        {
            var result = await _blockchain.QualityCheckAsync(dto);
            if (!result)
                return BadRequest("Failed to record quality check.");
            return Ok("Quality check recorded.");
        }

        [HttpPost("ship")]
        public async Task<IActionResult> Ship([FromBody] ShipDTO dto)
        {
            var result = await _blockchain.ShipAsync(dto);
            if (!result)
                return BadRequest("Failed to record shipment.");
            return Ok("Shipment recorded.");
        }

        [HttpGet("history/{batchId}")]
        public async Task<IActionResult> History(string batchId)
        {
            var result = await _blockchain.GetHistoryAsync(batchId);
            return Ok(result);
        }
        [HttpGet("health")]
        public IActionResult Health()
        {
            var blockchainHealthy = _blockchain.HealthCheckAsync().Result;
            return Ok(new
            {
                status = "healthy",
                blockchain = blockchainHealthy ? "connected" : "disconnected"
            });
        }
    }
}
