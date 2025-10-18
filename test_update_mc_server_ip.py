#!/usr/bin/env python3
"""Unit tests for update_mc_server_ip.py"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
import tempfile
import shutil

from nbtlib import File, Compound, List, String

# Import functions from the script
from update_mc_server_ip import (
    extract_ip,
    load_servers_dat,
    save_servers_dat,
    upsert_server,
    fetch_dynamic_html,
    main,
)


class TestExtractIP:
    """Test IP extraction from HTML text"""

    def test_extract_simple_ipv4(self):
        """Should extract a simple IPv4 address"""
        html = "<html><body>Server IP: 192.168.1.100</body></html>"
        result = extract_ip(html)
        assert result == "192.168.1.100"

    def test_extract_ipv4_with_port(self):
        """Should extract IPv4 with port"""
        html = "Connect to: 192.168.1.100:25565"
        result = extract_ip(html)
        assert result == "192.168.1.100:25565"

    def test_extract_first_ip_when_multiple(self):
        """Should return first IP when multiple exist"""
        html = "Primary: 10.0.0.1 Backup: 10.0.0.2"
        result = extract_ip(html)
        assert result == "10.0.0.1"

    def test_no_ip_found_raises_error(self):
        """Should raise RuntimeError when no IP is found"""
        html = "<html><body>No IP address here!</body></html>"
        with pytest.raises(RuntimeError, match="Could not find an IP"):
            extract_ip(html)

    def test_extract_edge_case_ips(self):
        """Should handle edge case valid IPs"""
        # Test with 0.0.0.0
        assert extract_ip("IP: 0.0.0.0") == "0.0.0.0"
        # Test with high port
        assert extract_ip("IP: 127.0.0.1:65535") == "127.0.0.1:65535"


class TestLoadServersDat:
    """Test loading servers.dat NBT files"""

    def test_load_nonexistent_file(self):
        """Should create empty servers structure for nonexistent file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.dat"
            nbt, is_gzipped = load_servers_dat(path)

            assert isinstance(nbt, File)
            assert is_gzipped == False  # Default to uncompressed
            assert "servers" in nbt['']
            assert isinstance(nbt['']['servers'], List)
            assert len(nbt['']['servers']) == 0

    def test_load_existing_file_gzipped(self):
        """Should load existing gzipped servers.dat file correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "servers.dat"

            # Create a test NBT file (gzipped)
            test_nbt = File({'': Compound({
                "servers": List[Compound]([
                    Compound({
                        "name": String("Test Server"),
                        "ip": String("1.2.3.4:25565")
                    })
                ])
            })})
            test_nbt.save(path, gzipped=True)

            # Load it back
            loaded, is_gzipped = load_servers_dat(path)

            assert isinstance(loaded, File)
            assert is_gzipped == True  # Should detect gzipped format
            assert len(loaded['']['servers']) == 1
            assert str(loaded['']['servers'][0]["name"]) == "Test Server"
            assert str(loaded['']['servers'][0]["ip"]) == "1.2.3.4:25565"

    def test_load_existing_file_uncompressed(self):
        """Should load existing uncompressed servers.dat file correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "servers.dat"

            # Create a test NBT file (uncompressed - standard Minecraft format)
            test_nbt = File({'': Compound({
                "servers": List[Compound]([
                    Compound({
                        "name": String("MC Server"),
                        "ip": String("9.8.7.6:25565")
                    })
                ])
            })})
            test_nbt.save(path, gzipped=False)

            # Load it back
            loaded, is_gzipped = load_servers_dat(path)

            assert isinstance(loaded, File)
            assert is_gzipped == False  # Should detect uncompressed format
            assert len(loaded['']['servers']) == 1
            assert str(loaded['']['servers'][0]["name"]) == "MC Server"
            assert str(loaded['']['servers'][0]["ip"]) == "9.8.7.6:25565"


class TestUpsertServer:
    """Test server insertion and updating"""

    def test_insert_server_into_empty_list(self):
        """Should insert new server into empty list"""
        nbt = File({'': Compound({"servers": List[Compound]([])})})
        upsert_server(nbt, "New Server", "10.0.0.1:25565")

        servers = nbt['']['servers']
        assert len(servers) == 1
        assert str(servers[0]["name"]) == "New Server"
        assert str(servers[0]["ip"]) == "10.0.0.1:25565"

    def test_update_server_by_name(self):
        """Should update existing server when name matches"""
        nbt = File({'': Compound({
            "servers": List[Compound]([
                Compound({
                    "name": String("My Server"),
                    "ip": String("1.2.3.4:25565")
                })
            ])
        })})

        upsert_server(nbt, "My Server", "5.6.7.8:25565")

        servers = nbt['']['servers']
        assert len(servers) == 1
        assert str(servers[0]["name"]) == "My Server"
        assert str(servers[0]["ip"]) == "5.6.7.8:25565"

    def test_update_server_by_ip(self):
        """Should update existing server when IP matches"""
        nbt = File({'': Compound({
            "servers": List[Compound]([
                Compound({
                    "name": String("Old Name"),
                    "ip": String("1.2.3.4:25565")
                })
            ])
        })})

        upsert_server(nbt, "New Name", "1.2.3.4:25565")

        servers = nbt['']['servers']
        assert len(servers) == 1
        assert str(servers[0]["name"]) == "New Name"
        assert str(servers[0]["ip"]) == "1.2.3.4:25565"

    def test_insert_multiple_servers(self):
        """Should insert multiple different servers"""
        nbt = File({'': Compound({"servers": List[Compound]([])})})

        upsert_server(nbt, "Server 1", "1.1.1.1")
        upsert_server(nbt, "Server 2", "2.2.2.2")

        servers = nbt['']['servers']
        assert len(servers) == 2
        assert str(servers[0]["name"]) == "Server 1"
        assert str(servers[1]["name"]) == "Server 2"


class TestSaveServersDat:
    """Test saving servers.dat files"""

    def test_save_creates_file(self):
        """Should create file when saving"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "new_servers.dat"
            nbt = File({'': Compound({"servers": List[Compound]([])})})

            save_servers_dat(nbt, path)

            assert path.exists()

    def test_save_creates_backup(self):
        """Should create backup when overwriting existing file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "servers.dat"
            backup_path = path.with_suffix(".dat_backup")

            # Create original file (uncompressed)
            original_nbt = File({'': Compound({
                "servers": List[Compound]([
                    Compound({"name": String("Original"), "ip": String("1.1.1.1")})
                ])
            })})
            original_nbt.save(path, gzipped=False)
            original_content = path.read_bytes()

            # Save new content (uncompressed)
            new_nbt = File({'': Compound({
                "servers": List[Compound]([
                    Compound({"name": String("Updated"), "ip": String("2.2.2.2")})
                ])
            })})
            save_servers_dat(new_nbt, path, gzipped=False)

            # Verify backup exists and contains original data
            assert backup_path.exists()
            assert backup_path.read_bytes() == original_content

            # Verify new file has updated data
            loaded = File.load(path, gzipped=False)
            assert str(loaded['']['servers'][0]["name"]) == "Updated"

    def test_save_preserves_format(self):
        """Should save in the format specified by gzipped parameter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "servers.dat"
            nbt = File({'': Compound({"servers": List[Compound]([])})})

            # Test gzipped format
            save_servers_dat(nbt, path, gzipped=True)
            loaded_gz, is_gz = load_servers_dat(path)
            assert is_gz == True

            # Test uncompressed format
            save_servers_dat(nbt, path, gzipped=False)
            loaded_unc, is_unc = load_servers_dat(path)
            assert is_unc == False


class TestFetchDynamicHTML:
    """Test Playwright-based dynamic HTML fetching"""

    @patch('playwright.sync_api.sync_playwright')
    def test_fetch_dynamic_html_success(self, mock_playwright):
        """Should fetch and return rendered HTML using Playwright"""
        # Setup mock Playwright objects
        mock_page = Mock()
        mock_page.content.return_value = "<html><body>IP: 192.168.1.1</body></html>"

        mock_browser = Mock()
        mock_browser.new_page.return_value = mock_page

        mock_p = Mock()
        mock_p.chromium.launch.return_value = mock_browser

        mock_playwright.return_value.__enter__.return_value = mock_p

        # Call the function
        html = fetch_dynamic_html("https://example.com")

        # Verify
        assert "192.168.1.1" in html
        mock_p.chromium.launch.assert_called_once_with(headless=True)
        mock_page.goto.assert_called_once()
        mock_browser.close.assert_called_once()

    @patch('builtins.__import__', side_effect=ImportError("No module named 'playwright'"))
    def test_fetch_dynamic_html_playwright_not_installed(self, mock_import):
        """Should raise helpful error when Playwright not installed"""
        with pytest.raises(RuntimeError, match="Playwright is not installed"):
            fetch_dynamic_html("https://example.com")


class TestMainIntegration:
    """Integration test for main() function"""

    @patch('update_mc_server_ip.requests.get')
    @patch('update_mc_server_ip.INSTANCE_DIR')
    @patch('update_mc_server_ip.SERVER_NAME', 'Test Server')
    def test_main_end_to_end(self, mock_instance_dir, mock_get):
        """Should fetch IP, update servers.dat, and save correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock HTTP response
            mock_response = Mock()
            mock_response.text = "<html>Server IP: 10.20.30.40:25565</html>"
            mock_get.return_value = mock_response

            # Setup temp directory - patch to return tmpdir as string
            servers_dat = Path(tmpdir) / "servers.dat"

            with patch('update_mc_server_ip.INSTANCE_DIR', tmpdir):
                # Run main
                main()

                # Verify file was created and contains correct data
                assert servers_dat.exists()

                # Use load_servers_dat to auto-detect format
                loaded, _ = load_servers_dat(servers_dat)
                servers = loaded['']['servers']
                assert len(servers) == 1
                assert str(servers[0]["name"]) == "Test Server"
                assert str(servers[0]["ip"]) == "10.20.30.40:25565"

    @patch('update_mc_server_ip.fetch_dynamic_html')
    @patch('update_mc_server_ip.requests.get')
    @patch('update_mc_server_ip.INSTANCE_DIR')
    @patch('update_mc_server_ip.SERVER_NAME', 'Test Server')
    def test_main_fallback_to_playwright(self, mock_instance_dir, mock_get, mock_fetch):
        """Should fall back to Playwright when requests doesn't find IP"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mock HTTP response WITHOUT an IP
            mock_response = Mock()
            mock_response.text = "<html>No IP address here!</html>"
            mock_get.return_value = mock_response

            # Setup Playwright fallback to return HTML with IP
            mock_fetch.return_value = "<html>Dynamic IP: 99.88.77.66:12345</html>"

            # Setup temp directory
            servers_dat = Path(tmpdir) / "servers.dat"

            with patch('update_mc_server_ip.INSTANCE_DIR', tmpdir):
                # Run main
                main()

                # Verify Playwright was called as fallback
                mock_fetch.assert_called_once()

                # Verify file was created with IP from Playwright
                assert servers_dat.exists()
                # Use load_servers_dat to auto-detect format
                loaded, _ = load_servers_dat(servers_dat)
                servers = loaded['']['servers']
                assert len(servers) == 1
                assert str(servers[0]["ip"]) == "99.88.77.66:12345"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
