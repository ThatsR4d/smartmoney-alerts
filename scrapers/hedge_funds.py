"""
Hedge Fund 13F Filing Scraper

Scrapes 13F-HR filings from SEC EDGAR to track institutional holdings.
13F filings show what hedge funds, mutual funds, and institutions hold.
Filed quarterly, within 45 days of quarter end.
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
import sys

# Handle imports
try:
    from config.settings import SEC_USER_AGENT, SEC_BASE_URL
    from config.tickers import SP500, MEME_STOCKS, MAGNIFICENT_7
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import SEC_USER_AGENT, SEC_BASE_URL
    from config.tickers import SP500, MEME_STOCKS, MAGNIFICENT_7


# Famous investors/funds to track
FAMOUS_FUNDS = {
    "BERKSHIRE HATHAWAY": {"manager": "Warren Buffett", "cik": "0001067983"},
    "SCION ASSET MANAGEMENT": {"manager": "Michael Burry", "cik": "0001649339"},
    "PERSHING SQUARE": {"manager": "Bill Ackman", "cik": "0001336528"},
    "BRIDGEWATER ASSOCIATES": {"manager": "Ray Dalio", "cik": "0001350694"},
    "RENAISSANCE TECHNOLOGIES": {"manager": "Jim Simons", "cik": "0001037389"},
    "CITADEL ADVISORS": {"manager": "Ken Griffin", "cik": "0001423053"},
    "TIGER GLOBAL": {"manager": "Chase Coleman", "cik": "0001167483"},
    "APPALOOSA": {"manager": "David Tepper", "cik": "0001006438"},
    "GREENLIGHT CAPITAL": {"manager": "David Einhorn", "cik": "0001079114"},
    "THIRD POINT": {"manager": "Dan Loeb", "cik": "0001040273"},
    "BAUPOST GROUP": {"manager": "Seth Klarman", "cik": "0001061768"},
    "LONE PINE CAPITAL": {"manager": "Stephen Mandel", "cik": "0001061165"},
    "COATUE MANAGEMENT": {"manager": "Philippe Laffont", "cik": "0001535392"},
    "DRUCKENMILLER": {"manager": "Stanley Druckenmiller", "cik": "0001536411"},
    "ICAHN": {"manager": "Carl Icahn", "cik": "0000921669"},
    "PAULSON": {"manager": "John Paulson", "cik": "0001035674"},
    "VIKING GLOBAL": {"manager": "Andreas Halvorsen", "cik": "0001103804"},
    "ELLIOTT MANAGEMENT": {"manager": "Paul Singer", "cik": "0001048445"},
}

# CIKs of famous funds for quick lookup
FAMOUS_CIKS = {v["cik"]: k for k, v in FAMOUS_FUNDS.items()}


class HedgeFundScraper:
    """Scraper for SEC 13F filings."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': SEC_USER_AGENT,
            'Accept-Encoding': 'gzip, deflate',
        })
        self.base_url = "https://www.sec.gov"
        self.rss_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=13F-HR&company=&dateb=&owner=include&count=100&output=atom"

    def scrape_recent_filings(self, max_filings: int = 50) -> List[Dict]:
        """Scrape recent 13F filings from SEC RSS feed."""
        print(f"Scraping up to {max_filings} recent 13F filings...")

        try:
            response = self.session.get(self.rss_url, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('.//atom:entry', ns)

            print(f"Found {len(entries)} 13F entries in RSS feed")

            filings = []
            for i, entry in enumerate(entries[:max_filings]):
                try:
                    title_elem = entry.find('atom:title', ns)
                    link_elem = entry.find('atom:link', ns)

                    if title_elem is None or link_elem is None:
                        continue

                    title = title_elem.text
                    link = link_elem.get('href')

                    # Check if this is a famous fund (prioritize these)
                    is_famous = False
                    fund_name = None
                    manager_name = None

                    for fund_key, fund_info in FAMOUS_FUNDS.items():
                        if fund_key.lower() in title.lower():
                            is_famous = True
                            fund_name = fund_key
                            manager_name = fund_info["manager"]
                            break

                    # Parse the filing
                    filing = self._parse_filing(link, title, is_famous, fund_name, manager_name)
                    if filing:
                        filings.append(filing)
                        status = "⭐ FAMOUS" if is_famous else ""
                        print(f"  [{i+1}] {filing.get('fund_name', 'Unknown')[:30]} {status}")

                    time.sleep(0.15)  # Rate limit

                except Exception as e:
                    print(f"Error parsing 13F entry {i+1}: {e}")
                    continue

            print(f"Successfully parsed {len(filings)} 13F filings")
            return filings

        except Exception as e:
            print(f"Error scraping 13F RSS: {e}")
            return []

    def scrape_famous_funds(self) -> List[Dict]:
        """Specifically scrape filings from famous funds."""
        print("Scraping filings from famous hedge funds...")

        filings = []
        for fund_name, fund_info in FAMOUS_FUNDS.items():
            try:
                cik = fund_info["cik"]
                manager = fund_info["manager"]

                # Get recent filings for this CIK
                url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F-HR&dateb=&owner=include&count=5&output=atom"

                response = self.session.get(url, timeout=30)
                if response.status_code != 200:
                    continue

                root = ET.fromstring(response.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('.//atom:entry', ns)

                if entries:
                    # Get most recent filing
                    link_elem = entries[0].find('atom:link', ns)
                    if link_elem is not None:
                        link = link_elem.get('href')
                        filing = self._parse_filing(link, fund_name, True, fund_name, manager)
                        if filing:
                            filings.append(filing)
                            print(f"  ⭐ {manager}: {filing.get('position_count', 0)} positions")

                time.sleep(0.2)

            except Exception as e:
                print(f"Error scraping {fund_name}: {e}")
                continue

        return filings

    def _parse_filing(self, filing_url: str, title: str, is_famous: bool,
                      fund_name: str = None, manager_name: str = None) -> Optional[Dict]:
        """Parse a 13F filing to extract holdings."""
        try:
            response = self.session.get(filing_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract fund name from title if not provided
            if not fund_name:
                fund_name = title.split(' - ')[0] if ' - ' in title else title
                fund_name = re.sub(r'\s*\(.*?\)', '', fund_name).strip()

            # Find the information table XML
            xml_link = None
            table = soup.find('table', class_='tableFile')
            if table:
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        doc_type = cells[3].get_text(strip=True) if len(cells) > 3 else ''
                        if 'INFORMATION TABLE' in doc_type.upper() or 'INFOTABLE' in doc_type.upper():
                            link = cells[2].find('a')
                            if link:
                                href = link.get('href', '')
                                if href.endswith('.xml'):
                                    xml_link = self.base_url + href if href.startswith('/') else href
                                    break

            # Parse holdings from XML
            holdings = []
            total_value = 0

            if xml_link:
                holdings, total_value = self._parse_holdings_xml(xml_link)

            # Extract accession number
            accession_match = re.search(r'/(\d{10}-\d{2}-\d{6})', filing_url)
            accession_number = accession_match.group(1) if accession_match else None

            # Get filing date
            filing_date = datetime.now().strftime('%Y-%m-%d')
            date_elem = soup.find(string=re.compile(r'Filing Date', re.I))
            if date_elem:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(date_elem.parent))
                if date_match:
                    filing_date = date_match.group(1)

            # Get report date (quarter end)
            report_date = None
            report_elem = soup.find(string=re.compile(r'Period of Report', re.I))
            if report_elem:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(report_elem.parent))
                if date_match:
                    report_date = date_match.group(1)

            # Identify new, increased, decreased, exited positions
            # (Would need previous quarter's data for comparison - simplified here)
            top_holdings = sorted(holdings, key=lambda x: x.get('value', 0), reverse=True)[:20]

            return {
                'accession_number': accession_number,
                'filing_date': filing_date,
                'report_date': report_date,
                'filing_url': filing_url,
                'fund_name': fund_name,
                'manager_name': manager_name,
                'is_famous': is_famous,
                'total_value': total_value,
                'position_count': len(holdings),
                'top_holdings': json.dumps(top_holdings[:10]),
                'holdings': holdings,  # Full list for analysis
            }

        except Exception as e:
            print(f"Error parsing 13F filing {filing_url}: {e}")
            return None

    def _parse_holdings_xml(self, xml_url: str) -> Tuple[List[Dict], float]:
        """Parse 13F information table XML."""
        holdings = []
        total_value = 0

        try:
            response = self.session.get(xml_url, timeout=30)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            # Find all info table entries
            for entry in root.iter():
                if 'infotable' in entry.tag.lower():
                    holding = {}

                    for child in entry:
                        tag = child.tag.split('}')[-1].lower()  # Remove namespace

                        if 'nameofissuer' in tag:
                            holding['company_name'] = child.text
                        elif 'titleofclass' in tag:
                            holding['title'] = child.text
                        elif 'cusip' in tag:
                            holding['cusip'] = child.text
                        elif 'value' in tag:
                            try:
                                # Value is in thousands
                                holding['value'] = int(child.text) * 1000
                                total_value += holding['value']
                            except:
                                pass
                        elif 'sshprnamt' in tag:
                            try:
                                holding['shares'] = int(child.text)
                            except:
                                pass
                        elif 'sshprnamttype' in tag:
                            holding['share_type'] = child.text

                    if holding.get('company_name'):
                        # Try to get ticker
                        holding['ticker'] = self._match_ticker(holding.get('company_name', ''))
                        holdings.append(holding)

        except Exception as e:
            print(f"Error parsing holdings XML {xml_url}: {e}")

        return holdings, total_value

    def _match_ticker(self, company_name: str) -> Optional[str]:
        """Try to match company name to ticker."""
        if not company_name:
            return None

        from config.tickers import COMPANY_ALIASES

        name_upper = company_name.upper().strip()

        # Remove common suffixes
        for suffix in [' INC', ' CORP', ' CO', ' LTD', ' LLC', ' CLASS A', ' CLASS B', ' COM']:
            name_upper = name_upper.replace(suffix, '')

        # Check aliases
        for alias, ticker in COMPANY_ALIASES.items():
            if alias.replace(' INC', '').replace(' CORP', '') in name_upper:
                return ticker

        return None


class HedgeFundAnalyzer:
    """Analyzer for 13F filings."""

    def analyze(self, filing: Dict) -> Dict:
        """Analyze a 13F filing for notable activity."""
        anomalies = []
        anomaly_texts = []

        # Famous fund
        if filing.get('is_famous'):
            anomalies.append('famous_fund')
            manager = filing.get('manager_name', 'Famous manager')
            anomaly_texts.append(f"{manager}'s latest moves revealed")

        # Large portfolio
        total_value = filing.get('total_value', 0)
        if total_value >= 10_000_000_000:
            anomalies.append('huge_portfolio')
            anomaly_texts.append(f"${total_value/1e9:.1f}B portfolio")
        elif total_value >= 1_000_000_000:
            anomalies.append('billion_portfolio')
            anomaly_texts.append(f"${total_value/1e9:.1f}B portfolio")

        # Check top holdings for interesting stocks
        top_holdings = filing.get('top_holdings', '[]')
        if isinstance(top_holdings, str):
            try:
                top_holdings = json.loads(top_holdings)
            except:
                top_holdings = []

        for holding in top_holdings[:5]:
            ticker = holding.get('ticker', '')
            if ticker in MEME_STOCKS:
                anomalies.append('meme_stock_holding')
                anomaly_texts.append(f"Holds meme stock ${ticker}")
                break
            if ticker in MAGNIFICENT_7:
                anomalies.append('mag7_holding')
                break

        filing['anomalies'] = json.dumps(anomalies)
        filing['anomaly_texts'] = anomaly_texts

        return filing


class HedgeFundScorer:
    """Virality scorer for 13F filings."""

    def score(self, filing: Dict) -> int:
        """Calculate virality score (0-100)."""
        score = 0

        # Famous fund (max 35)
        if filing.get('is_famous'):
            score += 35
        else:
            score += 5

        # Portfolio size (max 25)
        total_value = filing.get('total_value', 0)
        if total_value >= 50_000_000_000:
            score += 25
        elif total_value >= 10_000_000_000:
            score += 20
        elif total_value >= 1_000_000_000:
            score += 15
        elif total_value >= 100_000_000:
            score += 10
        else:
            score += 5

        # Anomalies (max 25)
        anomalies = filing.get('anomalies', '[]')
        if isinstance(anomalies, str):
            try:
                anomalies = json.loads(anomalies)
            except:
                anomalies = []

        if 'meme_stock_holding' in anomalies:
            score += 15
        if 'famous_fund' in anomalies:
            score += 10

        # Position count suggests active trading
        position_count = filing.get('position_count', 0)
        if position_count >= 100:
            score += 10
        elif position_count >= 50:
            score += 5

        return min(score, 100)


# Instances
hedge_fund_scraper = HedgeFundScraper()
hedge_fund_analyzer = HedgeFundAnalyzer()
hedge_fund_scorer = HedgeFundScorer()


def scrape_hedge_fund_filings(max_filings: int = 50, famous_only: bool = False) -> List[Dict]:
    """Convenience function to scrape and analyze 13F filings."""
    if famous_only:
        filings = hedge_fund_scraper.scrape_famous_funds()
    else:
        filings = hedge_fund_scraper.scrape_recent_filings(max_filings)

    analyzed_filings = []
    for filing in filings:
        filing = hedge_fund_analyzer.analyze(filing)
        filing['virality_score'] = hedge_fund_scorer.score(filing)
        filing['tier'] = 1 if filing['virality_score'] >= 70 else 2 if filing['virality_score'] >= 50 else 3 if filing['virality_score'] >= 30 else 4
        analyzed_filings.append(filing)

    return analyzed_filings


if __name__ == "__main__":
    print("Testing Hedge Fund 13F Scraper...")
    print("=" * 60)

    # Test recent filings
    filings = scrape_hedge_fund_filings(max_filings=10)

    print(f"\nFound {len(filings)} filings")
    print("=" * 60)

    for filing in filings[:5]:
        print(f"\n{'⭐ ' if filing.get('is_famous') else ''}{filing.get('fund_name', 'Unknown')[:40]}")
        if filing.get('manager_name'):
            print(f"  Manager: {filing.get('manager_name')}")
        print(f"  Positions: {filing.get('position_count', 0)}")
        print(f"  Total Value: ${filing.get('total_value', 0)/1e9:.2f}B")
        print(f"  Score: {filing.get('virality_score')}/100 (Tier {filing.get('tier')})")

        # Show top holdings
        top = filing.get('top_holdings', '[]')
        if isinstance(top, str):
            top = json.loads(top)
        if top:
            print(f"  Top Holdings:")
            for h in top[:3]:
                ticker = h.get('ticker') or 'N/A'
                value = h.get('value', 0)
                print(f"    ${ticker}: ${value/1e6:.1f}M")
