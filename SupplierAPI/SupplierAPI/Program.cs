using SupplierAPI.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers()
    .AddJsonOptions(options =>
    {
        options.JsonSerializerOptions.PropertyNameCaseInsensitive = true;
        options.JsonSerializerOptions.PropertyNamingPolicy = null;
    });

builder.Services.AddEndpointsApiExplorer();

// Configure Blockchain Service (Option A: Pure Client)
builder.Services.Configure<BlockchainOptions>(
    builder.Configuration.GetSection("Blockchain"));

builder.Services.AddHttpClient();                     
builder.Services.AddSingleton<BlockchainService>();   
// Add CORS for development
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", builder =>
    {
        builder.AllowAnyOrigin()
               .AllowAnyMethod()
               .AllowAnyHeader();
    });
});

var app = builder.Build();



app.UseCors("AllowAll");
app.UseAuthorization();
app.MapControllers();



app.Run();