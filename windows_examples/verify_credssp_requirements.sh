#!/bin/bash
# Verify CredSSP requirements on Ansible controller
# Run this on your Ansible control node

echo "=== Checking CredSSP Requirements for Ansible ==="
echo ""

# Check Python version
echo "[1/4] Checking Python version..."
python3 --version 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✓ Python 3 is installed"
else
    echo "  ✗ Python 3 not found"
    exit 1
fi

# Check pywinrm
echo ""
echo "[2/4] Checking pywinrm installation..."
python3 -c "import winrm; print('  ✓ pywinrm version:', winrm.__version__)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  ✗ pywinrm not installed"
    echo "  Install with: pip3 install pywinrm"
fi

# Check requests-credssp
echo ""
echo "[3/4] Checking requests-credssp (required for CredSSP)..."
python3 -c "import requests_credssp; print('  ✓ requests-credssp is installed')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "  ✗ requests-credssp not installed - THIS IS REQUIRED FOR CREDSSP!"
    echo ""
    echo "  Install with one of:"
    echo "    pip3 install pywinrm[credssp]"
    echo "    pip3 install requests-credssp"
    echo ""
    echo "  Or on RHEL/Rocky/CentOS:"
    echo "    sudo dnf install -y python3-requests-credssp"
    echo ""
    echo "  Or on Ubuntu/Debian:"
    echo "    sudo apt-get install -y python3-requests-credssp"
    MISSING_CREDSSP=1
fi

# Check pywinrm with credssp support
echo ""
echo "[4/4] Testing WinRM with CredSSP support..."
python3 << 'EOF' 2>/dev/null
try:
    import winrm
    from winrm.protocol import Protocol
    import requests_credssp

    # Check if credssp is available as a transport
    # This doesn't actually connect, just verifies the library supports it
    print("  ✓ WinRM library supports CredSSP authentication")
    print("  ✓ All requirements met!")
except ImportError as e:
    print(f"  ✗ Import error: {e}")
    print("  Install pywinrm[credssp] package")
except Exception as e:
    print(f"  Warning: {e}")
EOF

if [ $? -ne 0 ]; then
    echo "  ✗ CredSSP support not available"
fi

# Summary
echo ""
echo "=== Summary ==="
if [ -n "$MISSING_CREDSSP" ]; then
    echo "❌ CredSSP NOT READY - install requests-credssp package"
    echo ""
    echo "Quick fix:"
    echo "  pip3 install --user pywinrm[credssp]"
    echo ""
    exit 1
else
    echo "✅ CredSSP requirements are installed"
    echo ""
    echo "You can now use CredSSP authentication in your playbooks:"
    echo "  ansible_winrm_transport: credssp"
    echo ""
fi

# Test connectivity example
echo "To test WinRM connectivity:"
echo "  ansible windows -i hosts -m win_ping"
echo ""
echo "Example inventory for CredSSP:"
echo "---"
echo "[windows]"
echo "your-server.example.com"
echo ""
echo "[windows:vars]"
echo "ansible_user=ec2-user"
echo "ansible_password=PASSW0RD"
echo "ansible_connection=winrm"
echo "ansible_winrm_transport=credssp"
echo "ansible_winrm_server_cert_validation=ignore"
echo "ansible_winrm_port=5986"
echo "ansible_winrm_scheme=https"
echo ""
