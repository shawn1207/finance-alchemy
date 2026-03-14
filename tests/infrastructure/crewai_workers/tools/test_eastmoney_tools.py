import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from src.infrastructure.crewai_workers.tools.eastmoney_tools import (
    EastmoneySelectStockTool,
)


@pytest.fixture
def mock_httpx_client():
    """Fixture to mock httpx.Client and its post method."""
    # This is the correct target for patching because the code uses `with httpx.Client(...)`
    with patch("src.infrastructure.crewai_workers.tools.eastmoney_tools.httpx.Client") as mock_client_constructor:
        # 1. Mock the response object that post() will return
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": 0,
            "data": {
                "code": "100",
                "data": {
                    "result": {
                        "dataList": [
                            {
                                "f12": "600519",
                                "f14": "贵州茅台",
                                "f2": "1500.00",
                                "f3": "1.5",
                                "f9": "25.00",
                                "f23": "30.00",
                            },
                            {
                                "f12": "000858",
                                "f14": "五粮液",
                                "f2": "150.00",
                                "f3": "2.0",
                                "f9": "20.00",
                                "f23": "25.00",
                            },
                        ],
                        "columns": [
                            {"key": "f12", "title": "代码"},
                            {"key": "f14", "title": "名称"},
                            {"key": "f2", "title": "最新价"},
                            {"key": "f3", "title": "涨跌幅"},
                            {"key": "f9", "title": "市盈率(PE)"},
                            {"key": "f23", "title": "市净率(PB)"},
                        ]
                    }
                }
            }
        }
        mock_response.raise_for_status.return_value = None

        # 2. Mock the client instance that the constructor returns
        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        
        # 3. The __enter__ method is what's called by `with`, it should return the instance
        mock_client_instance.__enter__.return_value = mock_client_instance

        # 4. Make the constructor return our mocked instance
        mock_client_constructor.return_value = mock_client_instance
        
        yield mock_client_constructor


def test_eastmoney_select_stock_tool_get_list(mock_httpx_client):
    """Test the get_stock_list method of the EastmoneySelectStockTool."""
    tool = EastmoneySelectStockTool()
    args = {"keyword": "市盈率<30"}

    # Execute the tool's method
    result_df = tool.get_stock_list(**args)

    # Assertions
    assert isinstance(result_df, pd.DataFrame)
    assert not result_df.empty
    assert len(result_df) == 2
    assert "代码" in result_df.columns
    assert "市盈率(PE)" in result_df.columns

    # Check content
    assert result_df.iloc[0]["代码"] == "600519"
    assert result_df.iloc[1]["名称"] == "五粮液"

    # Verify that the client was constructed and post was called
    mock_httpx_client.assert_called_once()
    client_instance = mock_httpx_client.return_value
    client_instance.post.assert_called_once()
    call_kwargs = client_instance.post.call_args.kwargs
    assert "json" in call_kwargs
    assert call_kwargs["json"]["keyword"] == "市盈率<30"

