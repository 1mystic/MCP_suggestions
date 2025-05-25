import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPServerFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_mcpservers_org(self):
        """Fetch MCP servers from mcpservers.org"""
        try:
            url = "https://mcpservers.org/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            servers = []
            
            # Look for server cards/entries (adjust selectors based on actual site structure)
            server_cards = soup.find_all(['div', 'article'], class_=re.compile(r'server|card|entry', re.I))
            
            for card in server_cards:
                try:
                    name_elem = card.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'title|name|header', re.I))
                    desc_elem = card.find(['p', 'div'], class_=re.compile(r'description|desc|summary', re.I))
                    
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        description = desc_elem.get_text(strip=True) if desc_elem else ""
                        
                        # Extract keywords from description
                        keywords = self._extract_keywords_from_text(description + " " + name)
                        
                        servers.append({
                            "name": name,
                            "description": description,
                            "keywords": keywords,
                            "source": "mcpservers.org",
                            "use_case_trigger": self._generate_use_case_trigger(description)
                        })
                except Exception as e:
                    logger.warning(f"Error parsing server card: {e}")
                    continue
            
            return servers
        except Exception as e:
            logger.error(f"Error fetching from mcpservers.org: {e}")
            return []

    def fetch_awesome_mcp_servers(self):
        """Fetch MCP servers from awesome-mcp-servers GitHub repo"""
        try:
            # Get README content from GitHub API
            api_url = "https://api.github.com/repos/appcypher/awesome-mcp-servers/readme"
            response = self.session.get(api_url, timeout=10)
            response.raise_for_status()
            
            readme_data = response.json()
            readme_content = readme_data['content']
            
            # Decode base64 content
            import base64
            readme_text = base64.b64decode(readme_content).decode('utf-8')
            
            servers = self._parse_awesome_readme(readme_text)
            return servers
            
        except Exception as e:
            logger.error(f"Error fetching from awesome-mcp-servers: {e}")
            return []

    def _parse_awesome_readme(self, readme_text):
        """Parse the awesome-mcp-servers README for server entries"""
        servers = []
        lines = readme_text.split('\n')
        
        current_section = ""
        for line in lines:
            # Track sections
            if line.startswith('##'):
                current_section = line.strip('#').strip()
                continue
            
            # Look for markdown links that might be MCP servers
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            matches = re.findall(link_pattern, line)
            
            for name, url in matches:
                if 'mcp' in name.lower() or 'server' in name.lower():
                    # Extract description from the same line
                    description = line.split(']')[-1].strip(' -').strip()
                    
                    keywords = self._extract_keywords_from_text(description + " " + name + " " + current_section)
                    
                    servers.append({
                        "name": name,
                        "description": description,
                        "keywords": keywords,
                        "source": "awesome-mcp-servers",
                        "github_url": url if 'github.com' in url else None,
                        "use_case_trigger": self._generate_use_case_trigger(description),
                        "category": current_section
                    })
        
        return servers

    def _extract_keywords_from_text(self, text):
        """Extract relevant keywords from description text"""
        # Common technical keywords that might indicate MCP capabilities
        keyword_patterns = [
            r'\b(database|sql|postgres|mysql|mongodb)\b',
            r'\b(api|rest|graphql|http)\b',
            r'\b(file|filesystem|directory|storage)\b',
            r'\b(search|query|find|lookup)\b',
            r'\b(automation|script|command|terminal)\b',
            r'\b(browser|web|ui|frontend|selenium|playwright|puppeteer)\b',
            r'\b(git|github|version|control|repository)\b',
            r'\b(test|testing|validation|e2e)\b',
            r'\b(memory|cache|store|persist)\b',
            r'\b(observability|monitoring|metrics|logs)\b',
            r'\b(refactor|transform|migrate|analyze)\b'
        ]
        
        keywords = []
        text_lower = text.lower()
        
        for pattern in keyword_patterns:
            matches = re.findall(pattern, text_lower)
            keywords.extend(matches)
        
        # Remove duplicates and return
        return list(set(keywords))

    def _generate_use_case_trigger(self, description):
        """Generate a use case trigger based on description"""
        if not description:
            return "General utility MCP server."
        
        desc_lower = description.lower()
        
        if any(word in desc_lower for word in ['database', 'sql', 'query']):
            return "Task involves database operations or data management."
        elif any(word in desc_lower for word in ['browser', 'web', 'ui', 'automation']):
            return "Task involves web automation or browser interactions."
        elif any(word in desc_lower for word in ['file', 'filesystem', 'directory']):
            return "Task involves file system operations or file management."
        elif any(word in desc_lower for word in ['search', 'find', 'lookup']):
            return "Task requires searching or information retrieval."
        elif any(word in desc_lower for word in ['git', 'github', 'repository']):
            return "Task involves version control or repository management."
        else:
            return f"Useful for tasks involving: {description[:100]}..."

    def fetch_all_servers(self):
        """Fetch servers from all sources"""
        all_servers = []
        
        logger.info("Fetching from mcpservers.org...")
        mcpservers_org_data = self.fetch_mcpservers_org()
        all_servers.extend(mcpservers_org_data)
        
        logger.info("Fetching from awesome-mcp-servers...")
        awesome_servers_data = self.fetch_awesome_mcp_servers()
        all_servers.extend(awesome_servers_data)
        
        # Remove duplicates based on name
        unique_servers = {}
        for server in all_servers:
            key = server['name'].lower().strip()
            if key not in unique_servers:
                unique_servers[key] = server
        
        return list(unique_servers.values())

    def save_to_file(self, servers, filename="mcp_servers_cache.json"):
        """Save fetched servers to a JSON file"""
        data = {
            "last_updated": datetime.now().isoformat(),
            "server_count": len(servers),
            "servers": servers
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(servers)} MCP servers to {filename}")

if __name__ == "__main__":
    fetcher = MCPServerFetcher()
    servers = fetcher.fetch_all_servers()
    fetcher.save_to_file(servers)
    print(f"Fetched {len(servers)} MCP servers")