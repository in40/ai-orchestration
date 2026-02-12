"""
Performance Benchmarking for MCP Server Concurrent Request Handling
Measures throughput, latency, and resource utilization under concurrent load
"""
import asyncio
import time
import statistics
import aiohttp
import matplotlib.pyplot as plt
from typing import List, Dict, Any
import json
import threading
from mcp_server.server import McpServer


class PerformanceBenchmark:
    """Performance benchmarking for concurrent request handling"""
    
    def __init__(self, server_port: int = 3034):
        self.server_port = server_port
        self.base_url = f"http://127.0.0.1:{server_port}"
        self.results = []
    
    async def single_request(self, session: aiohttp.ClientSession, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a single request and record timing"""
        start_time = time.time()
        
        payload = {
            "jsonrpc": "2.0",
            "id": f"bench-{int(start_time * 1000000)}",
            "method": method
        }
        
        if params:
            payload["params"] = params
        
        try:
            async with session.post(f"{self.base_url}/send", json=payload) as response:
                result = await response.json()
        except Exception as e:
            result = {"error": str(e)}
        
        end_time = time.time()
        
        return {
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "method": method,
            "result": result
        }
    
    async def run_concurrent_load_test(self, num_requests: int, concurrency_level: int, method: str, params: Dict[str, Any] = None):
        """Run a concurrent load test"""
        print(f"Running load test: {num_requests} requests at {concurrency_level} concurrent")
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # Create all request tasks
            tasks = [
                self.single_request(session, method, params)
                for _ in range(num_requests)
            ]
            
            # Process tasks with specified concurrency limit
            semaphore = asyncio.Semaphore(concurrency_level)
            
            async def controlled_request(task):
                async with semaphore:
                    return await task
            
            controlled_tasks = [controlled_request(task) for task in tasks]
            results = await asyncio.gather(*controlled_tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate metrics
        durations = [r["duration"] for r in results]
        successful_requests = sum(1 for r in results if "error" not in r["result"])
        
        metrics = {
            "total_requests": num_requests,
            "concurrency_level": concurrency_level,
            "total_time": total_time,
            "requests_per_second": num_requests / total_time,
            "successful_requests": successful_requests,
            "failed_requests": num_requests - successful_requests,
            "success_rate": successful_requests / num_requests * 100,
            "avg_response_time": statistics.mean(durations),
            "median_response_time": statistics.median(durations),
            "p95_response_time": sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            "p99_response_time": sorted(durations)[int(len(durations) * 0.99)] if durations else 0,
            "min_response_time": min(durations) if durations else 0,
            "max_response_time": max(durations) if durations else 0,
            "results": results
        }
        
        print(f"Completed: {num_requests} requests in {total_time:.2f}s")
        print(f"RPS: {metrics['requests_per_second']:.2f}")
        print(f"Success Rate: {metrics['success_rate']:.2f}%")
        print(f"Avg Response Time: {metrics['avg_response_time']*1000:.2f}ms")
        print(f"P95 Response Time: {metrics['p95_response_time']*1000:.2f}ms")
        print(f"P99 Response Time: {metrics['p99_response_time']*1000:.2f}ms")
        
        return metrics
    
    async def run_progressive_load_test(self):
        """Run progressive load test with increasing concurrency"""
        configs = [
            (50, 1),    # 50 requests, 1 concurrent
            (50, 2),    # 50 requests, 2 concurrent
            (50, 5),    # 50 requests, 5 concurrent
            (100, 5),   # 100 requests, 5 concurrent
            (100, 10),  # 100 requests, 10 concurrent
            (200, 10),  # 200 requests, 10 concurrent
            (200, 20),  # 200 requests, 20 concurrent
        ]
        
        results = []
        
        for num_requests, concurrency in configs:
            print(f"\n--- Testing {num_requests} requests at {concurrency} concurrency ---")
            result = await self.run_concurrent_load_test(
                num_requests=num_requests,
                concurrency_level=concurrency,
                method="initialize",
                params={"clientInfo": {"name": "benchmark-client", "version": "1.0.0"}}
            )
            results.append(result)
        
        return results
    
    def plot_results(self, results: List[Dict[str, Any]]):
        """Plot benchmark results"""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            
            # Extract data
            labels = [f"{r['total_requests']}@{r['concurrency_level']}" for r in results]
            rps_values = [r['requests_per_second'] for r in results]
            avg_times = [r['avg_response_time'] * 1000 for r in results]  # Convert to ms
            p95_times = [r['p95_response_time'] * 1000 for r in results]  # Convert to ms
            success_rates = [r['success_rate'] for r in results]
            
            # Plot 1: Requests per second
            ax1.bar(range(len(labels)), rps_values)
            ax1.set_title('Requests Per Second')
            ax1.set_xlabel('Test Config (Requests@Concurrency)')
            ax1.set_ylabel('RPS')
            ax1.set_xticks(range(len(labels)))
            ax1.set_xticklabels(labels, rotation=45, ha='right')
            
            # Plot 2: Average response time
            ax2.plot(range(len(labels)), avg_times, marker='o', label='Avg')
            ax2.plot(range(len(labels)), p95_times, marker='s', label='P95')
            ax2.set_title('Response Times')
            ax2.set_xlabel('Test Config (Requests@Concurrency)')
            ax2.set_ylabel('Time (ms)')
            ax2.set_xticks(range(len(labels)))
            ax2.set_xticklabels(labels, rotation=45, ha='right')
            ax2.legend()
            
            # Plot 3: Success rate
            ax3.bar(range(len(labels)), success_rates)
            ax3.set_title('Success Rate')
            ax3.set_xlabel('Test Config (Requests@Concurrency)')
            ax3.set_ylabel('Success Rate (%)')
            ax3.set_ylim(90, 101)  # Focus on high success rates
            ax3.set_xticks(range(len(labels)))
            ax3.set_xticklabels(labels, rotation=45, ha='right')
            
            # Plot 4: Concurrency vs Performance
            concurrencies = [r['concurrency_level'] for r in results]
            ax4.scatter(concurrencies, rps_values, s=100, alpha=0.7)
            ax4.set_title('Concurrency vs Performance')
            ax4.set_xlabel('Concurrency Level')
            ax4.set_ylabel('Requests Per Second')
            
            plt.tight_layout()
            plt.savefig('benchmark_results.png', dpi=300, bbox_inches='tight')
            print("Benchmark results chart saved as 'benchmark_results.png'")
            
        except ImportError:
            print("Matplotlib not available, skipping chart generation")
            # Print tabular results instead
            print("\nBenchmark Results:")
            print("Config\t\tRPS\t\tAvg(ms)\tP95(ms)\tSuccess%")
            for r in results:
                config = f"{r['total_requests']}@{r['concurrency_level']}"
                print(f"{config}\t\t{r['requests_per_second']:.2f}\t\t{r['avg_response_time']*1000:.2f}\t{r['p95_response_time']*1000:.2f}\t{r['success_rate']:.2f}%")
    
    async def run_full_benchmark(self):
        """Run the complete benchmark suite"""
        print("Starting MCP Server Performance Benchmark")
        print("="*50)
        
        # Run progressive load test
        results = await self.run_progressive_load_test()
        
        # Generate plots
        self.plot_results(results)
        
        print("\nBenchmark completed!")


async def run_benchmark():
    """Function to run the benchmark with a test server"""
    # Create and start server
    server = McpServer(
        transport_type="http",
        host="127.0.0.1",
        port=3034,
        max_concurrent_requests=25
    )
    
    # Start server in background
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(3)
    
    try:
        # Run benchmarks
        benchmark = PerformanceBenchmark(server_port=3034)
        await benchmark.run_full_benchmark()
    finally:
        # Stop server
        server.stop()


if __name__ == "__main__":
    asyncio.run(run_benchmark())