# Configuration Loader Class
import json
import logging
from pathlib import Path


class ConfigLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.configs = {}
        
        self.config_dir.mkdir(exist_ok=True) # If a directory doesn't exist, we should error out imo, why are we making one? The app depends on the contents of the directory

    def load_all_configs(self):
        """Load all configuration files from the config directory."""
        try:
            for config_file in self.config_dir.glob("*.json"): # Again, this app runs on the basis of the entire contents of config, we should consider adding each required field, and throw an error otherwise
                config_name = config_file.stem
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        self.configs[config_name] = json.load(f)
                except Exception as e:
                    logging.error(f"Error loading {config_file}: {str(e)}")
                    raise ValueError(f"Failed to load config file: {config_file}")
            return self.configs
        except Exception as e:
            logging.error(f"Error in load_all_configs: {str(e)}")
            raise

    def get_config(self, config_name: str):
        """Get a specific configuration by name."""
        try:
            if config_name not in self.configs:
                config_file = self.config_dir / f"{config_name}.json"
                if not config_file.exists():
                    raise FileNotFoundError(f"Config file not found: {config_file}")
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        self.configs[config_name] = json.load(f)
                # What are we doing about other errors?
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON in {config_file}: {str(e)}")
                    raise
            return self.configs[config_name]
        except Exception as e:
            logging.error(f"Error getting config {config_name}: {str(e)}")
            raise