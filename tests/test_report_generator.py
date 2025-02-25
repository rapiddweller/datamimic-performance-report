import json
from unittest.mock import patch, MagicMock

import pytest

from app.report_components.report_generator import (
    aggregate_report_data,
    generate_html_report
)


class TestAggregateReportData:
    """Tests for aggregate_report_data function"""

    @patch('app.report_components.report_generator.process_report_throughput_data')
    @patch('app.report_components.report_generator.process_report_memory_data')
    @patch('app.report_components.report_generator.process_overall_throughput')
    def test_basic_aggregation(self, mock_overall, mock_memory, mock_throughput):
        """Test basic aggregation of report data"""
        # Setup mock return values
        mock_throughput.return_value = {
            "script1": {
                "measured": [{"version": "v1", "data": [{"x": 1, "y": 10}]}],
                "interpolated": [{"version": "v1", "data": [{"x": 1, "y": 10}, {"x": 2, "y": 20}]}]
            }
        }
        
        mock_memory.return_value = {
            "script1": {
                "single_process": [{"version": "v1", "data": [{"x": 100, "y": 2}]}],
                "multi_process": {2: [{"version": "v1", "data": [{"x": 200, "y": 4}]}]}
            }
        }
        
        mock_overall.return_value = [{"version": "v1", "throughput": 15.0}]
        
        # Call the function with sample data
        results = [{"script": "script1", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 10}]
        output = aggregate_report_data(results)
        
        # Verify the function calls
        mock_throughput.assert_called_once()
        mock_memory.assert_called_once_with(results)
        mock_overall.assert_called_once_with(results)
        
        # Check output structure
        assert "overallThroughput_json" in output
        assert "throughputByScriptMeasured_json" in output
        assert "throughputByScriptInterpolated_json" in output
        assert "memoryByScriptSingle_json" in output
        assert "memoryByScriptMulti_json" in output
        
        # Verify JSON content
        assert json.loads(output["overallThroughput_json"]) == [{"version": "v1", "throughput": 15.0}]
        assert json.loads(output["throughputByScriptMeasured_json"]) == {
            "script1": [{"version": "v1", "data": [{"x": 1, "y": 10}]}]
        }
        assert json.loads(output["throughputByScriptInterpolated_json"]) == {
            "script1": [{"version": "v1", "data": [{"x": 1, "y": 10}, {"x": 2, "y": 20}]}]
        }
        assert json.loads(output["memoryByScriptSingle_json"]) == {
            "script1": [{"version": "v1", "data": [{"x": 100, "y": 2}]}]
        }
        assert json.loads(output["memoryByScriptMulti_json"]) == {
            "script1": {
                "2": [{"version": "v1", "data": [{"x": 200, "y": 4}]}]
            }
        }

    @patch('app.report_components.report_generator.process_report_throughput_data')
    @patch('app.report_components.report_generator.process_report_memory_data')
    @patch('app.report_components.report_generator.process_overall_throughput')
    def test_empty_results(self, mock_overall, mock_memory, mock_throughput):
        """Test with empty results"""
        # Setup mock return values for empty results
        mock_throughput.return_value = {}
        mock_memory.return_value = {}
        mock_overall.return_value = []
        
        # Call the function with empty data
        results = []
        output = aggregate_report_data(results)
        
        # Check output has all expected keys with empty JSON values
        assert json.loads(output["overallThroughput_json"]) == []
        assert json.loads(output["throughputByScriptMeasured_json"]) == {}
        assert json.loads(output["throughputByScriptInterpolated_json"]) == {}
        assert json.loads(output["memoryByScriptSingle_json"]) == {}
        assert json.loads(output["memoryByScriptMulti_json"]) == {}

    def test_target_processes_range(self):
        """Test that target processes are set correctly (1-20)"""
        with patch('app.report_components.report_generator.process_report_throughput_data') as mock_throughput:
            with patch('app.report_components.report_generator.process_report_memory_data') as mock_memory:
                with patch('app.report_components.report_generator.process_overall_throughput') as mock_overall:
                    # Set return values to avoid JSON serialization errors
                    mock_throughput.return_value = {}
                    mock_memory.return_value = {}
                    mock_overall.return_value = []
                    
                    results = [{"script": "test"}]
                    aggregate_report_data(results)
                    
                    # Check that target_processes was correctly set to range(1, 21)
                    args, _ = mock_throughput.call_args
                    target_processes = args[1]
                    assert target_processes == list(range(1, 21))
                    assert len(target_processes) == 20
                    assert target_processes[0] == 1
                    assert target_processes[-1] == 20


class TestGenerateHTMLReport:
    """Tests for generate_html_report function"""
    
    @patch('app.report_components.report_generator.process_report_throughput_data')
    @patch('app.report_components.report_generator.process_overall_throughput')
    @patch('jinja2.Environment')
    def test_basic_html_generation(self, mock_jinja_env, mock_overall, mock_throughput):
        """Test basic HTML report generation"""
        # Setup mock for throughput data
        mock_throughput.return_value = {
            "script1": {
                "measured": [{"version": "v1", "data": [{"x": 1, "y": 10}]}],
                "interpolated": [{"version": "v1", "data": [{"x": 1, "y": 10}, {"x": 2, "y": 20}]}]
            }
        }
        
        # Setup mock for overall throughput
        mock_overall.return_value = [{"version": "v1", "throughput": 15.0}]
        
        # Setup mock for Jinja template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Test Report</html>"
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template
        mock_jinja_env.return_value = mock_env
        
        # Call the function
        results = [
            {"script": "script1", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 10,
             "peak_memory": 2*1024*1024}
        ]
        output = generate_html_report("Test Report", results)
        
        # Verify calls
        mock_throughput.assert_called_once()
        mock_env.get_template.assert_called_once_with("report_template.html.j2")
        
        # Check the output
        assert output == "<html>Test Report</html>"
        
        # Verify template context
        context = mock_template.render.call_args[0][0]
        assert context["script_name"] == "Test Report"
        assert "rawThroughputDatasets" in context
        assert "smoothThroughputDatasets" in context
        assert "rawSingleMemoryDatasets" in context
        assert "rawMultiMemoryDatasets" in context
        assert "versionSummary" in context
        assert "overallThroughput" in context

    @patch('app.report_components.report_generator.process_report_throughput_data')
    @patch('app.report_components.report_generator.process_overall_throughput')
    @patch('jinja2.Environment')
    def test_empty_results_html(self, mock_jinja_env, mock_overall, mock_throughput):
        """Test HTML report generation with empty results"""
        # Setup mock for empty results
        mock_throughput.return_value = {}
        mock_overall.return_value = []
        
        # Setup mock for Jinja template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Empty Report</html>"
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template
        mock_jinja_env.return_value = mock_env
        
        # Call the function with empty data
        results = []
        output = generate_html_report("Empty Report", results)
        
        # Check the output
        assert output == "<html>Empty Report</html>"
        
        # Verify template context structure for empty data
        context = mock_template.render.call_args[0][0]
        assert context["script_name"] == "Empty Report"
        assert json.loads(context["rawThroughputDatasets"]) == []
        assert json.loads(context["smoothThroughputDatasets"]) == []
        assert json.loads(context["rawSingleMemoryDatasets"]) == []

    @patch('app.report_components.report_generator.process_report_throughput_data')
    @patch('jinja2.Environment')
    def test_multiple_scripts_and_versions(self, mock_jinja_env, mock_throughput):
        """Test HTML report with multiple scripts and versions"""
        # Setup mock for throughput data with multiple scripts and versions
        mock_throughput.return_value = {
            "script1": {
                "measured": [
                    {"version": "v1", "data": [{"x": 1, "y": 10}]},
                    {"version": "v2", "data": [{"x": 1, "y": 15}]}
                ],
                "interpolated": [
                    {"version": "v1", "data": [{"x": 1, "y": 10}, {"x": 2, "y": 20}]},
                    {"version": "v2", "data": [{"x": 1, "y": 15}, {"x": 2, "y": 30}]}
                ]
            },
            "script2": {
                "measured": [
                    {"version": "v1", "data": [{"x": 1, "y": 5}]}
                ],
                "interpolated": [
                    {"version": "v1", "data": [{"x": 1, "y": 5}, {"x": 2, "y": 10}]}
                ]
            }
        }
        
        # Setup mock for Jinja template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Multi Report</html>"
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template
        mock_jinja_env.return_value = mock_env
        
        # Call the function with multi-script data
        results = [
            {"script": "script1", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 10, 
             "peak_memory": 2*1024*1024},
            {"script": "script1", "version": "v2", "num_process": 1, "count": 100, "elapsed_time": 5, 
             "peak_memory": 1*1024*1024},
            {"script": "script2", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 20, 
             "peak_memory": 3*1024*1024}
        ]
        generate_html_report("Multi Report", results)
        
        # Verify context for multiple scripts and versions
        context = mock_template.render.call_args[0][0]
        raw_throughput = json.loads(context["rawThroughputDatasets"])
        
        # Check we have 3 datasets (script1-v1, script1-v2, script2-v1)
        assert len(raw_throughput) == 3
        
        # Verify labels contain script and version
        labels = [d["label"] for d in raw_throughput]
        assert "script1 - v1" in labels
        assert "script1 - v2" in labels
        assert "script2 - v1" in labels

    @patch('app.report_components.report_generator.process_report_throughput_data')
    @patch('jinja2.Environment')
    def test_memory_data_processing(self, mock_jinja_env, mock_throughput):
        """Test memory data processing in HTML report generation"""
        # Setup basic throughput data
        mock_throughput.return_value = {
            "script1": {
                "measured": [{"version": "v1", "data": [{"x": 1, "y": 10}]}],
                "interpolated": [{"version": "v1", "data": [{"x": 1, "y": 10}]}]
            }
        }
        
        # Setup mock for Jinja template
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Memory Report</html>"
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template
        mock_jinja_env.return_value = mock_env
        
        # Call the function with memory data
        results = [
            # Single process data
            {"script": "script1", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 10,
             "peak_memory": 2*1024*1024},
            # Multi-process data
            {"script": "script1", "version": "v1", "num_process": 2, "count": 200, "elapsed_time": 10,
             "peak_memory": 4*1024*1024},
            {"script": "script1", "version": "v1", "num_process": 2, "count": 300, "elapsed_time": 15,
             "peak_memory": 6*1024*1024},
            # Different version
            {"script": "script1", "version": "v2", "num_process": 1, "count": 100, "elapsed_time": 5,
             "peak_memory": 1*1024*1024}
        ]
        generate_html_report("Memory Report", results)
        
        # Verify memory datasets
        context = mock_template.render.call_args[0][0]
        
        # Check single process memory data
        single_memory = json.loads(context["rawSingleMemoryDatasets"])
        assert len(single_memory) == 2  # Two versions
        
        # Check multi-process memory data
        multi_memory = json.loads(context["rawMultiMemoryDatasets"])
        assert "v1" in multi_memory
        assert "2" in multi_memory["v1"]  # 2 processes
        
        # Check version summary
        version_summary = json.loads(context["versionSummary"])
        assert "v1" in version_summary
        assert "v2" in version_summary
        assert "avgThroughput" in version_summary["v1"]
        assert "avgMemory" in version_summary["v1"]
        assert "testCount" in version_summary["v1"] 