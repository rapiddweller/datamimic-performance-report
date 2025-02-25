from unittest.mock import patch

import pytest

from app.report_components.data_processor import (
    process_overall_throughput,
    process_report_memory_data,
    process_report_throughput_data,
)


@pytest.fixture
def sample_throughput_results():
    """Fixture providing a standard set of throughput results for testing"""
    return [
        {"script": "script1", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 10},
        {"script": "script1", "version": "v1", "num_process": 2, "count": 200, "elapsed_time": 10},
        {"script": "script1", "version": "v2", "num_process": 1, "count": 100, "elapsed_time": 5},
        {"script": "script1", "version": "v2", "num_process": 2, "count": 200, "elapsed_time": 5},
        {"script": "script2", "version": "v1", "num_process": 1, "count": 150, "elapsed_time": 15},
        {"script": "script2", "version": "v1", "num_process": 2, "count": 300, "elapsed_time": 15},
    ]


@pytest.fixture
def sample_memory_results():
    """Fixture providing a standard set of memory results for testing"""
    return [
        {
            "script": "script1", "version": "v1", "num_process": 1, "count": 100,
            "memory_timeline": [1*1024*1024, 2*1024*1024, 1.5*1024*1024]  # Peak 2MB
        },
        {
            "script": "script1", "version": "v1", "num_process": 2, "count": 200,
            "memory_timeline": [3*1024*1024, 4*1024*1024, 3.5*1024*1024]  # Peak 4MB
        },
        {
            "script": "script1", "version": "v2", "num_process": 1, "count": 100,
            "memory_timeline": [0.5*1024*1024, 1*1024*1024, 0.8*1024*1024]  # Peak 1MB
        },
        {
            "script": "script2", "version": "v1", "num_process": 1, "count": 150,
            "memory_timeline": [2*1024*1024, 3*1024*1024, 2.5*1024*1024]  # Peak 3MB
        },
    ]


class TestProcessReportThroughputData:
    """Tests for process_report_throughput_data function"""
    
    def test_basic_processing(self, sample_throughput_results):
        """Test basic processing of throughput data"""
        target_processes = [1, 2, 4]
        
        output = process_report_throughput_data(sample_throughput_results, target_processes)
        
        # Check structure
        assert len(output) == 2  # Two scripts
        assert "script1" in output
        assert "script2" in output
        
        # Check script1 data
        assert "measured" in output["script1"]
        assert "interpolated" in output["script1"]
        
        # Find v1 version data
        v1_measured = next(item for item in output["script1"]["measured"] if item["version"] == "v1")
        
        # Check values for script1, v1
        assert any(d["x"] == 1 and d["y"] == 10 for d in v1_measured["data"])  # 100/10 = 10
        assert any(d["x"] == 2 and d["y"] == 20 for d in v1_measured["data"])  # 200/10 = 20
        
        # Find v1 interpolated data
        v1_interp = next(item for item in output["script1"]["interpolated"] if item["version"] == "v1")
        
        # Check interpolated values
        assert any(d["x"] == 1 and d["y"] == 10 for d in v1_interp["data"])
        assert any(d["x"] == 2 and d["y"] == 20 for d in v1_interp["data"])

    @patch('app.report_components.data_processor.improved_interpolate')
    def test_interpolation_called(self, mock_interpolate, sample_throughput_results):
        """Test that interpolation is correctly called and used"""
        mock_interpolate.return_value = 42
        
        target_processes = [1, 2, 4]
        output = process_report_throughput_data(sample_throughput_results, target_processes)
        
        # Check that improved_interpolate was called
        assert mock_interpolate.called
        
        # Get the interpolated data for np=4 (which doesn't exist in the measurements)
        v1_interp = next(item for item in output["script1"]["interpolated"] if item["version"] == "v1")
        np4_data = next(d for d in v1_interp["data"] if d["x"] == 4)
        
        # The value should be our mocked return value (rounded to int)
        assert np4_data["y"] == 42

    def test_multiple_measurements_averaging(self):
        """Test that multiple measurements for the same configuration are correctly averaged"""
        results = [
            {"script": "script1", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 10},
            {"script": "script1", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 20},
        ]
        target_processes = [1]
        
        output = process_report_throughput_data(results, target_processes)
        
        # For np=1, we have (100/10 + 100/20)/2 = (10 + 5)/2 = 7.5, rounded to 8
        s1_measured = output["script1"]["measured"][0]["data"]
        assert s1_measured[0]["y"] == 8

    def test_multiple_versions(self, sample_throughput_results):
        """Test handling of multiple versions"""
        target_processes = [1]
        
        output = process_report_throughput_data(sample_throughput_results, target_processes)
        
        # Check we have both versions for script1
        versions = [item["version"] for item in output["script1"]["measured"]]
        assert "v1" in versions
        assert "v2" in versions
        
        # Check values
        for item in output["script1"]["measured"]:
            if item["version"] == "v1":
                assert item["data"][0]["y"] == 10  # 100/10
            elif item["version"] == "v2":
                assert item["data"][0]["y"] == 20  # 100/5

    def test_default_version(self):
        """Test default version handling when version is not specified"""
        results = [
            {"script": "script1", "num_process": 1, "count": 100, "elapsed_time": 10},
        ]
        target_processes = [1]
        
        output = process_report_throughput_data(results, target_processes)
        
        assert output["script1"]["measured"][0]["version"] == "current"

    def test_zero_elapsed_time(self):
        """Test handling of zero elapsed time (should not cause division by zero)"""
        results = [
            {"script": "script1", "version": "v1", "num_process": 1, "count": 100, "elapsed_time": 0},
        ]
        target_processes = [1]
        
        output = process_report_throughput_data(results, target_processes)
        
        assert output["script1"]["measured"][0]["data"][0]["y"] == 0

    def test_empty_results(self):
        """Test with empty results"""
        results = []
        target_processes = [1, 2, 4]
        
        output = process_report_throughput_data(results, target_processes)
        
        assert output == {}


class TestProcessReportMemoryData:
    """Tests for process_report_memory_data function"""
    
    def test_basic_processing(self, sample_memory_results):
        """Test basic processing of memory data"""
        output = process_report_memory_data(sample_memory_results)
        
        # Check structure
        assert "script1" in output
        assert "script2" in output
        assert "single_process" in output["script1"]
        assert "multi_process" in output["script1"]
        
        # Check script1 single process data
        s1_single = output["script1"]["single_process"]
        versions = [item["version"] for item in s1_single]
        assert "v1" in versions
        assert "v2" in versions
        
        # Find v1 version data
        v1_data = next(item for item in s1_single if item["version"] == "v1")
        assert v1_data["data"][0]["x"] == 100
        assert v1_data["data"][0]["y"] == 2  # 2MB
        
        # Check script1 multi-process data
        assert 2 in output["script1"]["multi_process"]
        mp_data = output["script1"]["multi_process"][2][0]
        assert mp_data["version"] == "v1"
        assert mp_data["data"][0]["x"] == 200
        assert mp_data["data"][0]["y"] == 4  # 4MB

    def test_multiple_measurements_averaging(self):
        """Test averaging of multiple measurements for memory data"""
        results = [
            {
                "script": "script1", 
                "version": "v1", 
                "num_process": 1,
                "count": 100, 
                "memory_timeline": [1*1024*1024, 2*1024*1024]  # Peak 2MB
            },
            {
                "script": "script1", 
                "version": "v1", 
                "num_process": 1,
                "count": 100, 
                "memory_timeline": [2*1024*1024, 4*1024*1024]  # Peak 4MB
            },
        ]
        
        output = process_report_memory_data(results)
        
        # Average peak should be (2+4)/2 = 3MB
        assert output["script1"]["single_process"][0]["data"][0]["y"] == 3

    def test_multiple_versions(self, sample_memory_results):
        """Test handling of multiple versions for memory data"""
        output = process_report_memory_data(sample_memory_results)
        
        # Check script1 has multiple versions
        versions = [item["version"] for item in output["script1"]["single_process"]]
        assert "v1" in versions
        assert "v2" in versions
        
        # Check values
        for item in output["script1"]["single_process"]:
            if item["version"] == "v1":
                assert item["data"][0]["y"] == 2  # 2MB
            elif item["version"] == "v2":
                assert item["data"][0]["y"] == 1  # 1MB

    def test_default_version(self):
        """Test default version handling when version is not specified"""
        results = [
            {
                "script": "script1", 
                "num_process": 1,
                "count": 100, 
                "memory_timeline": [2*1024*1024]  # 2MB
            },
        ]
        
        output = process_report_memory_data(results)
        
        assert output["script1"]["single_process"][0]["version"] == "current"

    def test_missing_memory_timeline(self):
        """Test handling of results missing memory timeline"""
        results = [
            {
                "script": "script1", 
                "version": "v1", 
                "num_process": 1,
                "count": 100, 
                # No memory_timeline
            },
        ]
        
        output = process_report_memory_data(results)
        
        # Should not include this script as there's no memory data
        assert output == {}

    def test_empty_memory_timeline(self):
        """Test handling of empty memory timeline"""
        results = [
            {
                "script": "script1", 
                "version": "v1", 
                "num_process": 1,
                "count": 100, 
                "memory_timeline": []
            },
        ]
        
        output = process_report_memory_data(results)
        
        # Should not include this script as there's no meaningful memory data
        assert output == {}

    def test_empty_results(self):
        """Test with empty results"""
        results = []
        
        output = process_report_memory_data(results)
        
        assert output == {}


class TestProcessOverallThroughput:
    """Tests for process_overall_throughput function"""
    
    def test_basic_processing(self, sample_throughput_results):
        """Test basic processing of overall throughput data"""
        output = process_overall_throughput(sample_throughput_results)
        
        # Check structure - should have v1 and v2
        versions = [item["version"] for item in output]
        assert "v1" in versions
        assert "v2" in versions
        
        # Find v1 and v2 data
        v1_data = next(item for item in output if item["version"] == "v1")
        v2_data = next(item for item in output if item["version"] == "v2")
        
        # Calculate expected values
        v1_throughputs = []
        for res in sample_throughput_results:
            if res.get("version") == "v1":
                v1_throughputs.append(res["count"] / res["elapsed_time"])
        expected_v1 = sum(v1_throughputs) / len(v1_throughputs)
        
        v2_throughputs = []
        for res in sample_throughput_results:
            if res.get("version") == "v2":
                v2_throughputs.append(res["count"] / res["elapsed_time"])
        expected_v2 = sum(v2_throughputs) / len(v2_throughputs)
        
        assert v1_data["throughput"] == expected_v1
        assert v2_data["throughput"] == expected_v2

    def test_default_version(self):
        """Test default version handling when version is not specified"""
        results = [
            {"script": "script1", "count": 100, "elapsed_time": 10},
        ]
        
        output = process_overall_throughput(results)
        
        assert output[0]["version"] == "current"
        assert output[0]["throughput"] == 10

    def test_zero_elapsed_time(self):
        """Test handling of zero elapsed time"""
        results = [
            {"script": "script1", "version": "v1", "count": 100, "elapsed_time": 0},
        ]
        
        output = process_overall_throughput(results)
        
        assert output[0]["throughput"] == 0

    def test_empty_results(self):
        """Test with empty results"""
        results = []
        
        output = process_overall_throughput(results)
        
        assert output == [] 