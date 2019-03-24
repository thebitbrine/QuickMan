# QuickMan.Lib
### Quick way to build self-hosted APIs


#### Example:
```C#
        private QuickMan API;
        public void Run()
        {
            API = new QuickMan();
            var Endpoints = new Dictionary<string, Action<HttpListenerContext>>();
            
            // Endpoint should not start with a '/'
            // i.e Endpoints.Add("/HelloWorld", HelloWorld); won't work
            // To add an endpoint: Endpoints.Add("EndpointName", EndpointMethod);
            Endpoints.Add("HelloWorld", HelloWorld);
            
            // Server now will start on http://localhost:1999/
            API.Start(Endpoints, 20 /*Maximum Simultaneous Connections*/);
        }

        // http://localhost:1999/HelloWorld
        public void HelloWorld(HttpListenerContext Context)
        {
            // You always have a respond to the request ASAP,
            // otherwise client will drop the connection after ~30 Seconds
            API.Respond("Hello World!", Context);
            Console.WriteLine($"Said 'Hello World!' to {Context.Request.UserHostAddress}");
        }
```
