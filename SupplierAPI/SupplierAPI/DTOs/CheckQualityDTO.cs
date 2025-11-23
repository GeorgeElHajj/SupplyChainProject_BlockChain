namespace SupplierAPI.DTOs
{
    public class QualityCheckDTO
    {
        public string BatchId { get; set; }
        public string Result { get; set; }
        public string Inspector { get; set; }
        public string SupplierName { get; set; }
    }
}
