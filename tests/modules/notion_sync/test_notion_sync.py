"""Tests for Notion sync module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from modules.notion_sync.models import NotionPage, NotionDocumentType
from modules.notion_sync.service import NotionAPIClient, NotionContentProcessor, NotionSyncService


class TestNotionAPIClient:
    """Test Notion API client."""
    
    def test_init(self):
        """Test client initialization."""
        client = NotionAPIClient("test_token")
        assert client.token == "test_token"
        assert "Bearer test_token" in client.headers["Authorization"]
    
    @pytest.mark.asyncio
    async def test_get_page(self):
        """Test getting page metadata."""
        client = NotionAPIClient("test_token")
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"id": "test", "title": "Test Page"}
            mock_response.raise_for_status = Mock()
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await client.get_page("test_page_id")
            
            assert result["id"] == "test"
            assert result["title"] == "Test Page"


class TestNotionContentProcessor:
    """Test content processing."""
    
    def test_extract_rich_text_simple(self):
        """Test extracting simple text."""
        rich_text = [
            {
                "type": "text",
                "text": {"content": "Hello world"},
                "annotations": {}
            }
        ]
        
        result = NotionContentProcessor._extract_rich_text(rich_text)
        assert result == "Hello world"
    
    def test_extract_rich_text_formatted(self):
        """Test extracting formatted text."""
        rich_text = [
            {
                "type": "text",
                "text": {"content": "Bold text"},
                "annotations": {"bold": True}
            },
            {
                "type": "text", 
                "text": {"content": " and "},
                "annotations": {}
            },
            {
                "type": "text",
                "text": {"content": "code"},
                "annotations": {"code": True}
            }
        ]
        
        result = NotionContentProcessor._extract_rich_text(rich_text)
        assert result == "**Bold text** and `code`"
    
    def test_blocks_to_markdown_paragraph(self):
        """Test converting paragraph blocks to markdown."""
        blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "This is a paragraph."},
                            "annotations": {}
                        }
                    ]
                }
            }
        ]
        
        result = NotionContentProcessor.blocks_to_markdown(blocks)
        assert "This is a paragraph." in result
    
    def test_blocks_to_markdown_headings(self):
        """Test converting heading blocks to markdown."""
        blocks = [
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Main Title"},
                            "annotations": {}
                        }
                    ]
                }
            },
            {
                "type": "heading_2", 
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Subtitle"},
                            "annotations": {}
                        }
                    ]
                }
            }
        ]
        
        result = NotionContentProcessor.blocks_to_markdown(blocks)
        assert "# Main Title" in result
        assert "## Subtitle" in result
    
    def test_blocks_to_markdown_lists(self):
        """Test converting list blocks to markdown."""
        blocks = [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Bullet item"},
                            "annotations": {}
                        }
                    ]
                }
            },
            {
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Numbered item"},
                            "annotations": {}
                        }
                    ]
                }
            }
        ]
        
        result = NotionContentProcessor.blocks_to_markdown(blocks)
        assert "- Bullet item" in result
        assert "1. Numbered item" in result
    
    def test_blocks_to_markdown_code(self):
        """Test converting code blocks to markdown."""
        blocks = [
            {
                "type": "code",
                "code": {
                    "language": "python",
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "print('Hello, world!')"},
                            "annotations": {}
                        }
                    ]
                }
            }
        ]
        
        result = NotionContentProcessor.blocks_to_markdown(blocks)
        assert "```python" in result
        assert "print('Hello, world!')" in result
        assert "```" in result


class TestNotionSyncService:
    """Test Notion sync service."""
    
    @patch("modules.notion_sync.service.get_settings")
    def test_init_no_token(self, mock_settings):
        """Test initialization without token."""
        mock_settings.return_value = Mock(notion_token=None)
        
        service = NotionSyncService()
        assert service.client is None
    
    @patch("modules.notion_sync.service.get_settings")
    def test_init_with_token(self, mock_settings):
        """Test initialization with token."""
        mock_settings.return_value = Mock(notion_token="test_token")
        
        service = NotionSyncService()
        assert service.client is not None
        assert service.client.token == "test_token"
    
    def test_get_rule_filename_architecture(self):
        """Test rule filename generation for architecture."""
        service = NotionSyncService()
        
        page = NotionPage(
            id="test",
            title="Test Architecture",
            url="https://notion.so/test",
            doc_type=NotionDocumentType.ARCHITECTURE,
            last_edited_time=datetime.now()
        )
        
        filename = service._get_rule_filename(page)
        assert filename == "notion-architecture.mdc"
    
    def test_get_rule_filename_module_spec(self):
        """Test rule filename generation for module spec."""
        service = NotionSyncService()
        
        page = NotionPage(
            id="test",
            title="WebhookReceiver Spec",
            url="https://notion.so/test",
            doc_type=NotionDocumentType.MODULE_SPEC,
            module_name="webhook_receiver",
            last_edited_time=datetime.now()
        )
        
        filename = service._get_rule_filename(page)
        assert filename == "notion-webhook_receiver-spec.mdc"
    
    def test_get_rule_filename_generic(self):
        """Test rule filename generation for generic documents."""
        service = NotionSyncService()
        
        page = NotionPage(
            id="test",
            title="API Requirements & Specs",
            url="https://notion.so/test",
            doc_type=NotionDocumentType.API_SPEC,
            last_edited_time=datetime.now()
        )
        
        filename = service._get_rule_filename(page)
        assert filename == "notion-api-requirements--specs.mdc"
    
    def test_generate_cursor_rule(self):
        """Test Cursor rule generation."""
        service = NotionSyncService()
        
        page = NotionPage(
            id="test",
            title="Test Document",
            url="https://notion.so/test",
            doc_type=NotionDocumentType.ARCHITECTURE,
            last_edited_time=datetime.now()
        )
        
        content = "# Test Content\n\nThis is a test."
        rule = service._generate_cursor_rule(page, content)
        
        assert "name: notion-architecture" in rule
        assert "alwaysApply: true" in rule
        assert "# Test Document" in rule
        assert "https://notion.so/test" in rule
        assert "This is a test." in rule
    
    def test_indent_content(self):
        """Test content indentation for YAML."""
        service = NotionSyncService()
        
        content = "Line 1\nLine 2\nLine 3"
        indented = service._indent_content(content, 2)
        
        lines = indented.split("\n")
        assert all(line.startswith("  ") for line in lines)
        assert "Line 1" in lines[0]
        assert "Line 2" in lines[1]
        assert "Line 3" in lines[2]


@pytest.mark.asyncio
class TestNotionSyncIntegration:
    """Integration tests for Notion sync."""
    
    @patch("modules.notion_sync.service.get_settings")
    async def test_sync_page_no_client(self, mock_settings):
        """Test sync page without client."""
        mock_settings.return_value = Mock(notion_token=None)
        
        service = NotionSyncService()
        page = NotionPage(
            id="test",
            title="Test Page",
            url="https://notion.so/test",
            doc_type=NotionDocumentType.ARCHITECTURE,
            last_edited_time=datetime.now()
        )
        
        result = await service.sync_page(page)
        assert result is None
    
    @patch("modules.notion_sync.service.get_settings")
    async def test_sync_all_pages_no_client(self, mock_settings):
        """Test sync all pages without client."""
        mock_settings.return_value = Mock(notion_token=None)
        
        service = NotionSyncService()
        result = await service.sync_all_pages()
        assert result == [] 