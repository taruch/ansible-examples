#!/usr/bin/env python3
"""
Custom Ansible filter plugins for certificate discovery
"""

from datetime import datetime


class FilterModule:
    """Custom filters for certificate data processing"""

    def filters(self):
        return {
            'combine_cert_data': self.combine_cert_data,
            'parse_cert_date': self.parse_cert_date,
            'days_until_expiry': self.days_until_expiry,
        }

    def combine_cert_data(self, cert_tuple):
        """
        Combine certificate file data with parsed certificate information

        Args:
            cert_tuple: tuple of (file_dict, expiration, subject, issuer)

        Returns:
            dict: Combined certificate data
        """
        if not isinstance(cert_tuple, (list, tuple)) or len(cert_tuple) < 4:
            return {}

        file_data = cert_tuple[0]
        expiration = cert_tuple[1] if len(cert_tuple) > 1 else "unknown"
        subject = cert_tuple[2] if len(cert_tuple) > 2 else "unknown"
        issuer = cert_tuple[3] if len(cert_tuple) > 3 else "unknown"

        return {
            'path': file_data.get('path', 'unknown'),
            'size': file_data.get('size', 0),
            'mode': file_data.get('mode', 'unknown'),
            'owner': file_data.get('uid', 'unknown'),
            'group': file_data.get('gid', 'unknown'),
            'modified_time': file_data.get('mtime', 0),
            'expiration': expiration.strip() if expiration else "unknown",
            'subject': subject.strip() if subject else "unknown",
            'issuer': issuer.strip() if issuer else "unknown",
            'days_to_expiry': self._calculate_days_to_expiry(expiration),
        }

    def parse_cert_date(self, date_string):
        """
        Parse OpenSSL date format to ISO8601

        Args:
            date_string: Date string from OpenSSL (e.g., "Jan 1 00:00:00 2025 GMT")

        Returns:
            str: ISO8601 formatted date or original string if parsing fails
        """
        if not date_string or date_string == "unknown":
            return "unknown"

        try:
            # OpenSSL format: "Jan 1 00:00:00 2025 GMT"
            dt = datetime.strptime(date_string.strip(), "%b %d %H:%M:%S %Y %Z")
            return dt.isoformat()
        except (ValueError, AttributeError):
            return date_string

    def days_until_expiry(self, expiration_date):
        """
        Calculate days until certificate expiry

        Args:
            expiration_date: Certificate expiration date string

        Returns:
            int: Days until expiry, or -1 if unknown/error
        """
        return self._calculate_days_to_expiry(expiration_date)

    def _calculate_days_to_expiry(self, date_string):
        """
        Internal method to calculate days to expiry

        Args:
            date_string: Date string from OpenSSL

        Returns:
            int: Days until expiry, or -1 if unknown/expired/error
        """
        if not date_string or date_string == "unknown" or date_string == "keystore":
            return -1

        try:
            # Try to parse OpenSSL date format
            expiry_date = datetime.strptime(date_string.strip(), "%b %d %H:%M:%S %Y %Z")
            now = datetime.utcnow()
            delta = expiry_date - now
            return max(0, delta.days)
        except (ValueError, AttributeError):
            # Try ISO8601 format
            try:
                if 'T' in date_string:
                    expiry_date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                    now = datetime.utcnow()
                    delta = expiry_date - now
                    return max(0, delta.days)
            except (ValueError, AttributeError):
                pass

        return -1
