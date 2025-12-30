"""
SEC EDGAR Form 4 Scraper

Form 4 = Insider trading disclosure
- Must be filed within 2 business days of trade
- Contains: insider info, company, transaction details
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import time
from typing import List, Dict, Optional
import os
import sys

# Handle imports for both module and direct execution
try:
    from config.settings import SEC_BASE_URL, SEC_USER_AGENT, MIN_TRANSACTION_VALUE
    from config.tickers import COMPANY_ALIASES
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import SEC_BASE_URL, SEC_USER_AGENT, MIN_TRANSACTION_VALUE
    from config.tickers import COMPANY_ALIASES


class SECForm4Scraper:
    """Scraper for SEC Form 4 filings."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': SEC_USER_AGENT,
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'application/atom+xml, application/xml, text/xml, */*',
        })
        self.base_url = "https://www.sec.gov"
        self.rss_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=only&count=100&output=atom"

    def scrape_recent_filings(self, max_filings: int = 100) -> List[Dict]:
        """
        Scrape recent Form 4 filings from SEC RSS feed.
        Returns list of parsed trade dictionaries.
        """
        print(f"Scraping up to {max_filings} recent Form 4 filings...")

        try:
            # Get RSS feed
            response = self.session.get(self.rss_url, timeout=30)
            response.raise_for_status()

            # Parse RSS
            root = ET.fromstring(response.content)

            # Handle namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('.//atom:entry', ns)

            print(f"Found {len(entries)} entries in RSS feed")

            trades = []
            for i, entry in enumerate(entries[:max_filings]):
                try:
                    # Extract basic info from RSS
                    title_elem = entry.find('atom:title', ns)
                    link_elem = entry.find('atom:link', ns)
                    updated_elem = entry.find('atom:updated', ns)

                    if title_elem is None or link_elem is None:
                        continue

                    title = title_elem.text
                    link = link_elem.get('href')
                    updated = updated_elem.text if updated_elem is not None else None

                    # Parse the filing detail page
                    trade = self._parse_filing(link, title, updated)
                    if trade and trade.get('total_value', 0) >= MIN_TRANSACTION_VALUE:
                        trades.append(trade)
                        print(f"  [{i+1}] ${trade.get('ticker', 'N/A')}: {trade.get('insider_role')} - ${trade.get('total_value', 0):,.0f}")

                    # Rate limit: SEC asks for max 10 requests/second
                    time.sleep(0.15)

                except Exception as e:
                    print(f"Error parsing filing {i+1}: {e}")
                    continue

            print(f"\nSuccessfully parsed {len(trades)} trades above ${MIN_TRANSACTION_VALUE:,}")
            return trades

        except Exception as e:
            print(f"Error scraping SEC RSS: {e}")
            return []

    def _parse_filing(self, filing_url: str, title: str, updated: str) -> Optional[Dict]:
        """Parse a single Form 4 filing page to extract trade details."""
        try:
            # Get the filing index page
            response = self.session.get(filing_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')

            # Find the XML file link (contains structured data)
            xml_link = None
            xml_candidates = []

            # Look for XML links in the document table
            table = soup.find('table', class_='tableFile')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        link = cells[2].find('a')
                        if link:
                            href = link.get('href', '')
                            # Skip XSL-transformed files and primary_doc
                            if href.endswith('.xml'):
                                if 'xsl' not in href.lower() and 'primary_doc' not in href.lower():
                                    xml_candidates.append(href)

            # Also look for links outside the table
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href.endswith('.xml') and 'xsl' not in href.lower() and 'primary_doc' not in href.lower():
                    if href not in xml_candidates:
                        xml_candidates.append(href)

            # Try each candidate XML file
            for href in xml_candidates:
                xml_link = self.base_url + href if href.startswith('/') else href
                result = self._parse_form4_xml(xml_link, filing_url)
                if result:
                    return result

            return None

        except Exception as e:
            print(f"Error parsing filing {filing_url}: {e}")
            return None

    def _parse_form4_xml(self, xml_url: str, filing_url: str) -> Optional[Dict]:
        """Parse Form 4 XML to extract trade details."""
        try:
            response = self.session.get(xml_url, timeout=30)
            response.raise_for_status()

            # Parse XML, handling potential encoding issues
            content = response.content
            root = ET.fromstring(content)

            # Extract issuer (company) info - try various element paths
            issuer = root.find('.//issuer')
            if issuer is None:
                issuer = root.find('.//{*}issuer')
            if issuer is None:
                # Try finding by tag name directly
                for elem in root.iter():
                    if 'issuer' in elem.tag.lower():
                        issuer = elem
                        break

            if issuer is None:
                return None

            company_cik = self._get_text_from_element(issuer, ['issuerCik', 'cik'])
            company_name = self._get_text_from_element(issuer, ['issuerName', 'name'])
            ticker = self._get_text_from_element(issuer, ['issuerTradingSymbol', 'tradingSymbol'])

            # Clean up ticker
            if ticker:
                ticker = ticker.upper().strip()
            else:
                # Try to match from company name
                ticker = self._match_ticker(company_name)

            # Extract reporting owner (insider) info
            owner = root.find('.//reportingOwner')
            if owner is None:
                owner = root.find('.//{*}reportingOwner')
            if owner is None:
                return None

            insider_cik = self._get_text_from_element(owner, ['rptOwnerCik', 'cik'])
            insider_name = self._get_text_from_element(owner, ['rptOwnerName', 'name']) or "Unknown"

            # Get relationship
            relationship = owner.find('.//reportingOwnerRelationship')
            if relationship is None:
                relationship = owner.find('.//{*}reportingOwnerRelationship')

            is_director = False
            is_officer = False
            is_ten_percent = False
            officer_title = None

            if relationship is not None:
                is_director = self._get_text_from_element(relationship, ['isDirector']) == '1'
                is_officer = self._get_text_from_element(relationship, ['isOfficer']) == '1'
                is_ten_percent = self._get_text_from_element(relationship, ['isTenPercentOwner']) == '1'
                officer_title = self._get_text_from_element(relationship, ['officerTitle'])

            # Determine insider role
            insider_role = self._determine_role(is_director, is_officer, is_ten_percent, officer_title)

            # Extract transaction details
            # Look for non-derivative transactions (regular stock)
            transactions = root.findall('.//nonDerivativeTransaction')
            if not transactions:
                transactions = root.findall('.//{*}nonDerivativeTransaction')

            if not transactions:
                return None

            # Aggregate all transactions in this filing
            total_shares = 0
            total_value = 0
            transaction_type = None
            price_per_share = None
            transaction_date = None
            shares_after = None

            for trans in transactions:
                # Transaction coding
                trans_coding = trans.find('.//transactionCoding')
                if trans_coding is None:
                    trans_coding = trans.find('.//{*}transactionCoding')

                if trans_coding is not None:
                    code = self._get_text_from_element(trans_coding, ['transactionCode'])
                    if code:
                        transaction_type = code

                # Skip if not a purchase (P) - we're mainly interested in buys
                if transaction_type not in ('P', 'S', 'A', 'M'):
                    continue

                # Transaction amounts
                amounts = trans.find('.//transactionAmounts')
                if amounts is None:
                    amounts = trans.find('.//{*}transactionAmounts')

                if amounts is not None:
                    # Get shares
                    shares_elem = amounts.find('.//transactionShares')
                    if shares_elem is None:
                        shares_elem = amounts.find('.//{*}transactionShares')
                    if shares_elem is not None:
                        shares_value = shares_elem.find('.//value')
                        if shares_value is None:
                            shares_value = shares_elem.find('.//{*}value')
                        if shares_value is not None and shares_value.text:
                            try:
                                total_shares += float(shares_value.text)
                            except ValueError:
                                pass

                    # Get price
                    price_elem = amounts.find('.//transactionPricePerShare')
                    if price_elem is None:
                        price_elem = amounts.find('.//{*}transactionPricePerShare')
                    if price_elem is not None:
                        price_value = price_elem.find('.//value')
                        if price_value is None:
                            price_value = price_elem.find('.//{*}value')
                        if price_value is not None and price_value.text:
                            try:
                                price_per_share = float(price_value.text)
                            except ValueError:
                                pass

                # Transaction date
                trans_date = trans.find('.//transactionDate')
                if trans_date is None:
                    trans_date = trans.find('.//{*}transactionDate')
                if trans_date is not None:
                    date_value = trans_date.find('.//value')
                    if date_value is None:
                        date_value = trans_date.find('.//{*}value')
                    if date_value is not None and date_value.text:
                        transaction_date = date_value.text

                # Post-transaction holdings
                post_holdings = trans.find('.//postTransactionAmounts')
                if post_holdings is None:
                    post_holdings = trans.find('.//{*}postTransactionAmounts')
                if post_holdings is not None:
                    shares_after_elem = post_holdings.find('.//sharesOwnedFollowingTransaction')
                    if shares_after_elem is None:
                        shares_after_elem = post_holdings.find('.//{*}sharesOwnedFollowingTransaction')
                    if shares_after_elem is not None:
                        value_elem = shares_after_elem.find('.//value')
                        if value_elem is None:
                            value_elem = shares_after_elem.find('.//{*}value')
                        if value_elem is not None and value_elem.text:
                            try:
                                shares_after = int(float(value_elem.text))
                            except ValueError:
                                pass

            # Calculate total value
            if total_shares and price_per_share:
                total_value = total_shares * price_per_share

            # Skip if no meaningful transaction found
            if total_shares == 0:
                return None

            # Extract accession number from URL
            accession_match = re.search(r'/(\d{10}-\d{2}-\d{6})', filing_url)
            accession_number = accession_match.group(1) if accession_match else None

            if not accession_number:
                # Try alternate format
                accession_match = re.search(r'/(\d+)/(\d{10}-\d{2}-\d{6})', filing_url)
                if accession_match:
                    accession_number = accession_match.group(2)

            if not accession_number:
                # Generate a unique ID from URL
                accession_number = filing_url.split('/')[-2] if '/' in filing_url else str(hash(filing_url))

            # Get filing date
            filing_date = datetime.now().strftime('%Y-%m-%d')  # Default to today
            period_report = root.find('.//periodOfReport')
            if period_report is None:
                period_report = root.find('.//{*}periodOfReport')
            if period_report is not None and period_report.text:
                filing_date = period_report.text

            return {
                'accession_number': accession_number,
                'filing_date': filing_date,
                'filing_url': filing_url,
                'ticker': ticker,
                'company_name': company_name,
                'company_cik': company_cik,
                'insider_name': insider_name,
                'insider_cik': insider_cik,
                'insider_role': insider_role,
                'is_director': 1 if is_director else 0,
                'is_officer': 1 if is_officer else 0,
                'is_ten_percent_owner': 1 if is_ten_percent else 0,
                'officer_title': officer_title,
                'transaction_type': transaction_type,
                'transaction_date': transaction_date,
                'shares': int(total_shares) if total_shares else 0,
                'price_per_share': round(price_per_share, 2) if price_per_share else None,
                'total_value': round(total_value, 2) if total_value else 0,
                'shares_owned_after': shares_after,
            }

        except ET.ParseError as e:
            print(f"XML Parse Error for {xml_url}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing XML {xml_url}: {e}")
            return None

    def _get_text_from_element(self, element, tag_names: List[str]) -> Optional[str]:
        """Try to get text from element using multiple possible tag names."""
        if element is None:
            return None

        for tag in tag_names:
            # Try direct child
            child = element.find(f'.//{tag}')
            if child is None:
                # Try with wildcard namespace
                child = element.find('.//{*}' + tag)
            if child is None:
                # Try case-insensitive search
                for elem in element.iter():
                    if tag.lower() in elem.tag.lower():
                        if elem.text:
                            return elem.text.strip()
                        # Check for value sub-element
                        value = elem.find('.//value')
                        if value is not None and value.text:
                            return value.text.strip()

            if child is not None:
                if child.text:
                    return child.text.strip()
                # Check for value sub-element
                value = child.find('.//value')
                if value is None:
                    value = child.find('.//{*}value')
                if value is not None and value.text:
                    return value.text.strip()

        return None

    def _determine_role(self, is_director: bool, is_officer: bool, is_ten_percent: bool, title: str) -> str:
        """Determine the insider's role for display."""
        if title:
            title_upper = title.upper()
            if 'CEO' in title_upper or 'CHIEF EXECUTIVE' in title_upper:
                return 'CEO'
            elif 'CFO' in title_upper or 'CHIEF FINANCIAL' in title_upper:
                return 'CFO'
            elif 'COO' in title_upper or 'CHIEF OPERATING' in title_upper:
                return 'COO'
            elif 'CTO' in title_upper or 'CHIEF TECHNOLOGY' in title_upper:
                return 'CTO'
            elif 'PRESIDENT' in title_upper:
                return 'President'
            elif 'VP' in title_upper or 'VICE PRESIDENT' in title_upper:
                return 'VP'
            elif 'DIRECTOR' in title_upper:
                return 'Director'
            elif 'GENERAL COUNSEL' in title_upper:
                return 'General Counsel'
            elif 'SECRETARY' in title_upper:
                return 'Secretary'
            else:
                # Return shortened title
                return title[:25] + '...' if len(title) > 25 else title

        if is_officer:
            return 'Officer'
        if is_director:
            return 'Director'
        if is_ten_percent:
            return '10% Owner'

        return 'Insider'

    def _match_ticker(self, company_name: str) -> Optional[str]:
        """Try to match company name to ticker symbol."""
        if not company_name:
            return None

        name_upper = company_name.upper().strip()

        # Remove common suffixes for matching
        for suffix in [', INC.', ', INC', ' INC.', ' INC', ' CORP.', ' CORP', ' LLC', ' LTD', ' CO.', ' CO']:
            name_upper = name_upper.replace(suffix, '')

        # Direct match
        if name_upper in COMPANY_ALIASES:
            return COMPANY_ALIASES[name_upper]

        # Partial match
        for alias, ticker in COMPANY_ALIASES.items():
            clean_alias = alias.replace(', INC.', '').replace(', INC', '').replace(' INC.', '').replace(' INC', '')
            if clean_alias in name_upper or name_upper in clean_alias:
                return ticker

        return None


# Test the scraper
if __name__ == "__main__":
    scraper = SECForm4Scraper()
    trades = scraper.scrape_recent_filings(max_filings=20)

    print("\n" + "=" * 60)
    print("SCRAPE RESULTS SUMMARY")
    print("=" * 60)

    for trade in trades:
        print(f"\nTicker: {trade.get('ticker') or 'N/A'}")
        print(f"Company: {trade.get('company_name')}")
        print(f"Insider: {trade.get('insider_name')} ({trade.get('insider_role')})")
        print(f"Type: {'BUY' if trade.get('transaction_type') == 'P' else trade.get('transaction_type')}")
        print(f"Shares: {trade.get('shares', 0):,}")
        print(f"Price: ${trade.get('price_per_share', 0):,.2f}")
        print(f"Value: ${trade.get('total_value', 0):,.2f}")
        print(f"Date: {trade.get('transaction_date')}")

    print(f"\n{'=' * 60}")
    print(f"Total trades found: {len(trades)}")
