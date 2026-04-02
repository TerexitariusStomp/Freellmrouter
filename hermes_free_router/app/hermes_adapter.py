import yaml
from typing import Dict, Any
from .registry import Provider
from .router import RouterEngine

class HermesAdapter:
    """Adapter to convert Router selections to Hermes-compatible configuration"""
    
    def __init__(self, router: RouterEngine):
        self.router = router
        
    def generate_hermes_config(self, provider: Provider) -> Dict[str, Any]:
        """Generate Hermes-ready config block"""
        config = self.router.get_hermes_config(provider)
        
        # Structure as expected by Hermes Agent config
        hermes_block = {
            "model": {
                "provider": config.get("provider"),
                "model": config.get("model")
            }
        }
        
        if "base_url" in config:
            hermes_block["model"]["base_url"] = config["base_url"]
        
        return hermes_block

    def to_yaml(self, config: Dict[str, Any]) -> str:
        """Convert config dictionary to YAML string"""
        return yaml.dump(config, default_flow_style=False)

    def print_hermes_config(self, provider: Provider):
        """Helper to print config to console"""
        config = self.generate_hermes_config(provider)
        print(self.to_yaml(config))
