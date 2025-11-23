using Microsoft.AspNetCore.Mvc;
using RetailerAPI.DTOs;
using RetailerAPI.Services;
using System.Threading.Tasks;

namespace RetailerAPI.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class RetailerController : ControllerBase
    {
        private readonly BlockchainService _blockchain;

        public RetailerController(BlockchainService blockchain)
        {
            _blockchain = blockchain;
        }

        [HttpPost("receive")]
        public async Task<IActionResult> Receive([FromBody] ReceiveRetailDTO dto)
        {
            var result = await _blockchain.ReceiveRetailAsync(dto);
            if (!result) return BadRequest("Failed to record reception.");
            return Ok("Retail reception recorded.");
        }

        [HttpPost("sold")]
        public async Task<IActionResult> Sold([FromBody] SaleDTO dto)
        {
            var result = await _blockchain.SoldAsync(dto);
            if (!result) return BadRequest("Failed to record sale.");
            return Ok("Sale recorded successfully.");
        }

        [HttpGet("verify/{batchId}")]
        public async Task<IActionResult> Verify(string batchId)
        {
            var result = await _blockchain.VerifyAsync(batchId);
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
