using Microsoft.AspNetCore.Mvc;
using DistributorAPI.DTOs;
using DistributorAPI.Services;
using System.Threading.Tasks;

namespace DistributorAPI.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class DistributorController : ControllerBase
    {
        private readonly BlockchainService _blockchain;

        public DistributorController(BlockchainService blockchain)
        {
            _blockchain = blockchain;
        }

        [HttpPost("receive")]
        public async Task<IActionResult> Receive([FromBody] ReceiveDTO dto)
        {
            var result = await _blockchain.ReceiveAsync(dto);
            if (!result) return BadRequest("Failed to record reception.");
            return Ok("Reception recorded.");
        }

        [HttpPost("store")]
        public async Task<IActionResult> Store([FromBody] StoreDTO dto)
        {
            var result = await _blockchain.StoreAsync(dto);
            if (!result) return BadRequest("Failed to record storage.");
            return Ok("Product stored successfully.");
        }

        [HttpPost("deliver")]
        public async Task<IActionResult> Deliver([FromBody] DeliverDTO dto)
        {
            var result = await _blockchain.DeliverAsync(dto);
            if (!result) return BadRequest("Failed to record delivery.");
            return Ok("Delivery recorded.");
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
