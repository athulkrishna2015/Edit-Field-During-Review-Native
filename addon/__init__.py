from . import reviewer
from .log_handler import setup_file_logging, logger

setup_file_logging()
logger.info("EFDRN loaded")

from aqt import mw, gui_hooks
from .config import on_config_action

def check_for_update_and_show_support():
    addon_package = mw.addonManager.addonFromModule(__name__)
    meta = mw.addonManager.addonMeta(addon_package)
    
    # Get current version from manifest
    manifest = mw.addonManager.addon_meta(addon_package).manifest
    current_version = manifest.get("version", "0.0.0")
    
    last_version = meta.get("last_version", "0.0.0")
    supporter_opt_out = meta.get("supporter_opt_out", False)
    
    if current_version != last_version:
        logger.info(f"Addon updated from {last_version} to {current_version}")
        meta["last_version"] = current_version
        mw.addonManager.writeAddonMeta(addon_package, meta)
        
        if not supporter_opt_out:
            logger.info("Opening Support tab automatically after update")
            # Open config on Support tab (index 1)
            on_config_action(mw.addonManager, addon_package, None, initial_tab=1)

gui_hooks.main_window_did_init.append(check_for_update_and_show_support)
