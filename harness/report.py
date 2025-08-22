#!/usr/bin/env python3
import os
import json
from typing import Dict, List, Any
from datetime import datetime

def _generate_memory_chart_js(workload_name: str, workload_results: List[Dict[str, Any]]) -> str:
    """
    Generate JavaScript for memory usage chart.
    
    Args:
        workload_name: Name of the workload
        workload_results: List of workload results
        
    Returns:
        JavaScript code for memory chart
    """
    # Check if we have memory profiles
    has_memory_profile = any("memory_profile" in result for result in workload_results)
    if not has_memory_profile:
        return ""
    
    # Extract memory data
    memory_datasets = []
    for i, result in enumerate(workload_results):
        if "memory_profile" in result:
            runtime = result["runtime"]
            profile = result["memory_profile"]
            
            # CPU memory
            if "cpu_memory" in profile and profile["cpu_memory"]:
                # Convert to MB
                cpu_data = [mem / (1024 * 1024) for mem in profile["cpu_memory"]]
                memory_datasets.append({
                    "label": f"{runtime} CPU",
                    "data": cpu_data,
                    "borderColor": f"rgba({54 + i*30}, {162 - i*20}, {235 - i*30}, 1)",
                    "backgroundColor": f"rgba({54 + i*30}, {162 - i*20}, {235 - i*30}, 0.2)",
                    "fill": False,
                    "tension": 0.1
                })
            
            # GPU memory
            if "gpu_memory" in profile and profile["gpu_memory"]:
                # Convert to MB
                gpu_data = [mem / (1024 * 1024) for mem in profile["gpu_memory"]]
                memory_datasets.append({
                    "label": f"{runtime} GPU",
                    "data": gpu_data,
                    "borderColor": f"rgba({255 - i*30}, {99 + i*20}, {132 + i*30}, 1)",
                    "backgroundColor": f"rgba({255 - i*30}, {99 + i*20}, {132 + i*30}, 0.2)",
                    "fill": False,
                    "tension": 0.1
                })
    
    if not memory_datasets:
        return ""
    
    # Get timestamps (convert to relative seconds)
    first_result = next((r for r in workload_results if "memory_profile" in r), None)
    if not first_result or "memory_profile" not in first_result or "timestamps" not in first_result["memory_profile"]:
        return ""
    
    timestamps = first_result["memory_profile"]["timestamps"]
    if not timestamps:
        return ""
    
    start_time = timestamps[0]
    labels = [f"{(t - start_time):.1f}s" for t in timestamps]
    
    return f"""
    // Memory chart for {workload_name}
    new Chart(document.getElementById('memory-chart-{workload_name}'), {{
        type: 'line',
        data: {{
            labels: {json.dumps(labels)},
            datasets: {json.dumps(memory_datasets)}
        }},
        options: {{
            responsive: true,
            scales: {{
                y: {{
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Memory (MB)'
                    }}
                }},
                x: {{
                    title: {{
                        display: true,
                        text: 'Time (seconds)'
                    }}
                }}
            }}
        }}
    }});
    """

def generate_report(results: Dict[str, Any], output_path: str) -> None:
    """
    Generate an HTML report from benchmark results.
    
    Args:
        results: Benchmark results dictionary
        output_path: Path to save the HTML report
    """
    # Extract run metadata
    run_id = results["run_id"]
    model = results["model"]
    runtimes = results["runtimes"]
    timestamp = results["timestamp"]
    
    # Start building HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Benchmark Report: {run_id}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            h1, h2, h3 {{
                color: #2c3e50;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .summary {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .summary-card {{
                background-color: #fff;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f8f9fa;
                font-weight: bold;
            }}
            tr:hover {{
                background-color: #f1f1f1;
            }}
            .chart {{
                width: 100%;
                height: 400px;
                margin-bottom: 30px;
            }}
            .workload-section {{
                margin-bottom: 40px;
            }}
            .runtime-comparison {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                margin-bottom: 20px;
            }}
            .runtime-card {{
                flex: 1;
                min-width: 300px;
                background-color: #fff;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 20px;
            }}
            .metric {{
                font-size: 24px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .metric-label {{
                font-size: 14px;
                color: #666;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                text-align: center;
                font-size: 14px;
                color: #666;
            }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Benchmark Report</h1>
                <p>Run ID: <strong>{run_id}</strong></p>
                <p>Model: <strong>{model}</strong></p>
                <p>Timestamp: <strong>{timestamp}</strong></p>
            </div>
    """
    
    # Add summary section
    html += """
            <h2>Summary</h2>
            <div class="summary">
                <div class="summary-card">
                    <h3>Benchmark Configuration</h3>
                    <p>Model: <strong>{}</strong></p>
                    <p>Runtimes: <strong>{}</strong></p>
                    <p>Workloads: <strong>{}</strong></p>
                </div>
            </div>
    """.format(model, ", ".join(runtimes), ", ".join(results["workloads"].keys()))
    
    # Process each workload
    for workload_name, workload_results in results["workloads"].items():
        html += f"""
            <div class="workload-section">
                <h2>Workload: {workload_name}</h2>
        """
        
        # Add comparison table
        html += """
                <h3>Runtime Comparison</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Runtime</th>
                            <th>p50 Latency (ms)</th>
                            <th>p95 Latency (ms)</th>
                            <th>p99 Latency (ms)</th>
                            <th>Tokens/sec</th>
                            <th>Error Rate</th>
                            {f'<th>TTFT (ms)</th>' if result.get('stream', False) else ''}
                            {f'<th>Token Rate</th>' if result.get('stream', False) else ''}
                            {'<th>Quality</th>' if any('rouge' in k or 'bleu' in k or 'factual' in k for k in result['summary'].keys()) else ''}
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for result in workload_results:
            runtime = result["runtime"]
            summary = result["summary"]
            is_streaming = result.get("stream", False)
            has_evaluation = any('rouge' in k or 'bleu' in k or 'factual' in k for k in summary.keys())
            
            # Calculate quality score if evaluation metrics are available
            quality_score = 0
            if has_evaluation:
                metrics_count = 0
                if 'avg_bleu' in summary:
                    quality_score += summary['avg_bleu']
                    metrics_count += 1
                if 'avg_rougeL' in summary:
                    quality_score += summary['avg_rougeL']
                    metrics_count += 1
                if 'avg_factual_accuracy' in summary:
                    quality_score += summary['avg_factual_accuracy']
                    metrics_count += 1
                if 'avg_bertscore_f1' in summary:
                    quality_score += summary['avg_bertscore_f1']
                    metrics_count += 1
                
                if metrics_count > 0:
                    quality_score = quality_score / metrics_count
            
            html += f"""
                        <tr>
                            <td>{runtime}</td>
                            <td>{summary["p50_latency_ms"]:.2f}</td>
                            <td>{summary["p95_latency_ms"]:.2f}</td>
                            <td>{summary["p99_latency_ms"]:.2f}</td>
                            <td>{summary["tokens_per_second"]:.2f}</td>
                            <td>{summary["error_rate"]*100:.2f}%</td>
                            {f'<td>{summary.get("avg_ttft_ms", 0):.2f}</td>' if is_streaming else ''}
                            {f'<td>{summary.get("avg_token_gen_rate", 0):.2f}</td>' if is_streaming else ''}
                            {f'<td>{quality_score:.4f}</td>' if has_evaluation else ''}
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
        """
        
        # Add charts
        html += f"""
                <h3>Latency Comparison</h3>
                <div class="chart">
                    <canvas id="latency-chart-{workload_name}"></canvas>
                </div>
                
                <h3>Throughput Comparison</h3>
                <div class="chart">
                    <canvas id="throughput-chart-{workload_name}"></canvas>
                </div>
        """
        
        # Add memory charts if available
        has_memory_profile = any("memory_profile" in result for result in workload_results)
        if has_memory_profile:
            html += f"""
                <h3>Memory Usage</h3>
                <div class="chart">
                    <canvas id="memory-chart-{workload_name}"></canvas>
                </div>
            """
        
        # Add runtime details
        html += """
                <h3>Runtime Details</h3>
                <div class="runtime-comparison">
        """
        
        for result in workload_results:
            runtime = result["runtime"]
            summary = result["summary"]
            
            # Check if we have evaluation metrics
            has_evaluation = any('rouge' in k or 'bleu' in k or 'factual' in k for k in summary.keys())
            
            # Calculate quality score if evaluation metrics are available
            quality_score = 0
            if has_evaluation:
                metrics_count = 0
                if 'avg_bleu' in summary:
                    quality_score += summary['avg_bleu']
                    metrics_count += 1
                if 'avg_rougeL' in summary:
                    quality_score += summary['avg_rougeL']
                    metrics_count += 1
                if 'avg_factual_accuracy' in summary:
                    quality_score += summary['avg_factual_accuracy']
                    metrics_count += 1
                if 'avg_bertscore_f1' in summary:
                    quality_score += summary['avg_bertscore_f1']
                    metrics_count += 1
                
                if metrics_count > 0:
                    quality_score = quality_score / metrics_count
            
            html += f"""
                    <div class="runtime-card">
                        <h4>{runtime}</h4>
                        <div class="metric">{summary["p50_latency_ms"]:.2f} ms</div>
                        <div class="metric-label">p50 Latency</div>
                        
                        <div class="metric">{summary["tokens_per_second"]:.2f}</div>
                        <div class="metric-label">Tokens/sec</div>
                        
                        <div class="metric">{summary["successful_requests"]}</div>
                        <div class="metric-label">Successful Requests</div>
                        
                        <div class="metric">{summary["error_rate"]*100:.2f}%</div>
                        <div class="metric-label">Error Rate</div>
                        
                        {f'<div class="metric">{quality_score:.4f}</div><div class="metric-label">Quality Score</div>' if has_evaluation else ''}
                    </div>
            """
        
        html += """
                </div>
            </div>
        """
    
    # Add JavaScript for charts
    html += """
            <script>
    """
    
    for workload_name, workload_results in results["workloads"].items():
        runtimes = [result["runtime"] for result in workload_results]
        p50_latencies = [result["summary"]["p50_latency_ms"] for result in workload_results]
        p95_latencies = [result["summary"]["p95_latency_ms"] for result in workload_results]
        throughputs = [result["summary"]["tokens_per_second"] for result in workload_results]
        
        # Latency chart
        html += f"""
                // Latency chart for {workload_name}
                new Chart(document.getElementById('latency-chart-{workload_name}'), {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(runtimes)},
                        datasets: [
                            {{
                                label: 'p50 Latency (ms)',
                                data: {json.dumps(p50_latencies)},
                                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                                borderColor: 'rgba(54, 162, 235, 1)',
                                borderWidth: 1
                            }},
                            {{
                                label: 'p95 Latency (ms)',
                                data: {json.dumps(p95_latencies)},
                                backgroundColor: 'rgba(255, 99, 132, 0.5)',
                                borderColor: 'rgba(255, 99, 132, 1)',
                                borderWidth: 1
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Latency (ms)'
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Throughput chart for {workload_name}
                new Chart(document.getElementById('throughput-chart-{workload_name}'), {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(runtimes)},
                        datasets: [
                            {{
                                label: 'Tokens/sec',
                                data: {json.dumps(throughputs)},
                                backgroundColor: 'rgba(75, 192, 192, 0.5)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1
                            }}
                        ]
                    }},
                    options: {{
                        responsive: true,
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                title: {{
                                    display: true,
                                    text: 'Tokens/sec'
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Memory chart if available
                {self._generate_memory_chart_js(workload_name, workload_results)}
        """
    
    # Close HTML
    html += """
            </script>
            <div class="footer">
                <p>Generated by TokenForge LLM Inference Benchmark Platform</p>
                <p>© 2025 TokenForge</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Write HTML to file
    with open(output_path, "w") as f:
        f.write(html)

if __name__ == "__main__":
    # Example usage
    with open("sample_results.json", "r") as f:
        results = json.load(f)
    
    generate_report(results, "report.html")
