using System;
using System.Collections.Generic;
using System.Net;
using System.Text;
using System.Text.Json;

namespace QuickMan.Lib
{
    class Program
    {
        static void Main(string[] args)
        {
            int port = 8002;
            int maxConnections = 1000;

            // Parse command line arguments
            if (args.Length > 0)
            {
                if (int.TryParse(args[0], out int parsedPort))
                {
                    port = parsedPort;
                }
            }

            if (args.Length > 1)
            {
                if (int.TryParse(args[1], out int parsedMaxConn))
                {
                    maxConnections = parsedMaxConn;
                }
            }

            // Define endpoints
            var endpoints = new Dictionary<string, Action<HttpListenerContext>>
            {
                { "", HandleHome },
                { "status", HandleStatus },
                { "info", HandleInfo },
                { "echo", HandleEcho },
                { "data", HandleData },
                { "hello", HandleHello },
                { "headers", HandleHeaders },
                { "benchmark", HandleBenchmark }
            };

            // Display startup information
            Console.WriteLine();
            Console.WriteLine("╔════════════════════════════════════════════════════════╗");
            Console.WriteLine("║          QuickMan C# - HTTP Server v1.0               ║");
            Console.WriteLine("╚════════════════════════════════════════════════════════╝");
            Console.WriteLine();
            Console.WriteLine("Configuration:");
            Console.WriteLine($"  Port:            {port}");
            Console.WriteLine($"  Max Connections: {maxConnections}");
            Console.WriteLine($"  Endpoints:       {endpoints.Count}");
            Console.WriteLine($"  Local IP:        {API.GetLocalIP()}");
            Console.WriteLine();
            Console.WriteLine("Available endpoints:");
            Console.WriteLine($"  http://localhost:{port}/");
            Console.WriteLine($"  http://localhost:{port}/status");
            Console.WriteLine($"  http://localhost:{port}/info");
            Console.WriteLine($"  http://localhost:{port}/echo?message=test");
            Console.WriteLine($"  http://localhost:{port}/data");
            Console.WriteLine($"  http://localhost:{port}/hello?name=YourName");
            Console.WriteLine($"  http://localhost:{port}/headers");
            Console.WriteLine($"  http://localhost:{port}/benchmark");
            Console.WriteLine();
            Console.WriteLine("Press Ctrl+C to stop the server");
            Console.WriteLine();
            Console.WriteLine("═══════════════════════════════════════════════════════════");
            Console.WriteLine();

            // Start server
            try
            {
                API.Start(port, endpoints, maxConnections);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error starting server: {ex.Message}");
            }
        }

        // Endpoint handlers
        static void HandleHome(HttpListenerContext context)
        {
            string html = @"<!DOCTYPE html>
<html>
<head><title>QuickMan C# Server</title></head>
<body>
<h1>Welcome to QuickMan C# Server!</h1>
<p>This is a high-performance HTTP server written in C#.</p>
<h2>Available Endpoints:</h2>
<ul>
<li><a href='/status'>/status</a> - Server status</li>
<li><a href='/info'>/info</a> - Request information</li>
<li><a href='/echo?message=Hello'>/echo?message=Hello</a> - Echo message</li>
<li><a href='/data'>/data</a> - Sample data</li>
<li><a href='/hello'>/hello</a> - Plain text response</li>
<li><a href='/headers'>/headers</a> - Custom headers</li>
<li><a href='/benchmark'>/benchmark</a> - Benchmark endpoint</li>
</ul>
</body>
</html>";

            API.Respond(context, html, "text/html");
        }

        static void HandleStatus(HttpListenerContext context)
        {
            var response = new
            {
                status = "running",
                message = "QuickMan C# server is operational"
            };

            API.Respond(context, JsonSerializer.Serialize(response));
        }

        static void HandleInfo(HttpListenerContext context)
        {
            var request = context.Request;
            var response = new
            {
                method = request.HttpMethod,
                path = request.RawUrl,
                query = request.QueryString.ToString(),
                user_agent = request.UserAgent ?? "Unknown"
            };

            API.Respond(context, JsonSerializer.Serialize(response));
        }

        static void HandleEcho(HttpListenerContext context)
        {
            string message = context.Request.QueryString["message"];

            if (!string.IsNullOrEmpty(message))
            {
                var response = new
                {
                    echo = message,
                    length = message.Length
                };

                API.Respond(context, JsonSerializer.Serialize(response));
            }
            else
            {
                var response = new
                {
                    status = 400,
                    message = "Missing 'message' query parameter"
                };

                context.Response.StatusCode = 400;
                API.Respond(context, JsonSerializer.Serialize(response));
            }
        }

        static void HandleData(HttpListenerContext context)
        {
            var response = new
            {
                users = new[]
                {
                    new { id = 1, name = "Alice", email = "alice@example.com" },
                    new { id = 2, name = "Bob", email = "bob@example.com" },
                    new { id = 3, name = "Charlie", email = "charlie@example.com" }
                },
                total = 3
            };

            API.Respond(context, JsonSerializer.Serialize(response));
        }

        static void HandleHello(HttpListenerContext context)
        {
            string name = context.Request.QueryString["name"];
            string text;

            if (!string.IsNullOrEmpty(name))
            {
                text = $"Hello, {name}! Welcome to QuickMan C# Server.";
            }
            else
            {
                text = "Hello, World! Welcome to QuickMan C# Server.";
            }

            API.Respond(context, text, "text/plain");
        }

        static void HandleHeaders(HttpListenerContext context)
        {
            context.Response.AddHeader("X-Custom-Header", "QuickMan");
            context.Response.AddHeader("X-Powered-By", "C# Language");
            context.Response.AddHeader("X-Version", "1.0");

            var response = new
            {
                message = "Check the response headers!"
            };

            API.Respond(context, JsonSerializer.Serialize(response));
        }

        static void HandleBenchmark(HttpListenerContext context)
        {
            var response = new
            {
                benchmark = true
            };

            API.Respond(context, JsonSerializer.Serialize(response));
        }
    }
}
