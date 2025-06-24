import os
import sys
import asyncio
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bin.connection_rcon import search_in_rcon


class DummyFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, message, ephemeral=False):
        self.sent.append((message, ephemeral))


class DummyInteraction:
    def __init__(self):
        self.followup = DummyFollowup()


@patch('bin.connection_rcon.requests.get')
def test_search_in_rcon_found(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "result": {
            "stats": [
                {"player": "TestPlayerOne", "player_id": "123"},
                {"player": "AnotherPlayer", "player_id": "456"},
            ]
        }
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    interaction = DummyInteraction()
    result = asyncio.run(search_in_rcon('http://api', 'testplayerone', interaction, server_name='Server1'))

    assert result is True
    assert interaction.followup.sent == [
        ("Server: Server1 - Player: TestPlayerOne, Player ID: 123", True)
    ]

@patch('bin.connection_rcon.requests.get')
def test_search_in_rcon_not_found(mock_get):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "result": {
            "stats": [
                {"player": "OtherPlayer", "player_id": "789"}
            ]
        }
    }
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    interaction = DummyInteraction()
    result = asyncio.run(search_in_rcon('http://api', 'nonexistent', interaction, server_name='Server1'))

    assert result is False
    assert interaction.followup.sent == []
