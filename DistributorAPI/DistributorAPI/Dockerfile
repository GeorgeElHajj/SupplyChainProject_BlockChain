FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

COPY ["DistributorAPI.csproj", "./"]
RUN dotnet restore "DistributorAPI.csproj"

COPY . .
RUN dotnet build "DistributorAPI.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "DistributorAPI.csproj" -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS final
WORKDIR /app
COPY --from=publish /app/publish .
COPY keys/ ./keys/
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

EXPOSE 80
ENV ASPNETCORE_URLS=http://+:80
ENV ASPNETCORE_ENVIRONMENT=Production

ENTRYPOINT ["dotnet", "DistributorAPI.dll"]