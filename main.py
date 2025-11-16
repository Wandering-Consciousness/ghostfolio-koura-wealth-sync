import logging
import os

from SyncKoura import SyncKoura
from pretty_print import pretty_print_table

template = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=template)
logger = logging.getLogger(__name__)

SYNCKOURA = "SYNCKOURA"
DELETE_ALL_ACTS = "DELETE_ALL_ACTS"
GET_ALL_ACTS = "GET_ALL_ACTS"

ghost_keys = os.environ.get("GHOST_KEY", "").split(",")
ghost_tokens = os.environ.get("GHOST_TOKEN", "").split(",")
koura_usernames = os.environ.get("KOURA_USERNAME", "").split(",")
koura_passwords = os.environ.get("KOURA_PASSWORD", "").split(",")
ghost_hosts = os.environ.get("GHOST_HOST", "https://ghostfol.io").split(",")
koura_account_ids = os.environ.get("KOURA_ACCOUNT_ID", "").split(",")
ghost_account_names = os.environ.get("GHOST_ACCOUNT_NAME", "Koura Wealth").split(",")
ghost_currencies = os.environ.get("GHOST_CURRENCY", "NZD").split(",")
operations = os.environ.get("OPERATION", SYNCKOURA).split(",")
ghost_koura_platforms = os.environ.get("GHOST_KOURA_PLATFORM", "").split(",")


if __name__ == '__main__':
    for i in range(len(operations)):
        ghost_host = ghost_hosts[i] if len(ghost_hosts) > i else ghost_hosts[-1]
        koura_username = koura_usernames[i] if len(koura_usernames) > i else koura_usernames[-1]
        koura_password = koura_passwords[i] if len(koura_passwords) > i else koura_passwords[-1]
        ghost_key = ghost_keys[i] if len(ghost_keys) > i else ghost_keys[-1]
        ghost_token = ghost_tokens[i] if len(ghost_tokens) > i else ghost_tokens[-1]
        koura_account_id = koura_account_ids[i] if len(koura_account_ids) > i else koura_account_ids[-1]
        ghost_account_name = ghost_account_names[i] if len(ghost_account_names) > i else ghost_account_names[-1]
        ghost_currency = ghost_currencies[i] if len(ghost_currencies) > i else ghost_currencies[-1]
        ghost_koura_platform = ghost_koura_platforms[i] if len(ghost_koura_platforms) > i else ghost_koura_platforms[-1]

        ghost = SyncKoura(ghost_host, koura_username, koura_password, ghost_key, ghost_token, koura_account_id,
                         ghost_account_name, ghost_currency, ghost_koura_platform)

        if operations[i] == SYNCKOURA:
            logger.info("Starting sync for account %s: %s", i, koura_account_ids[i] if len(koura_account_ids) > i else "Unknown")
            ghost.sync_koura()
            logger.info("End sync")
        elif operations[i] == GET_ALL_ACTS:
            logger.info("Getting all activities")
            logger.info("Start of operation")
            table_data = []
            activities = ghost.get_all_acts_for_account()
            for activity in activities:
                table_data.append([activity['id'], activity['SymbolProfile']['name'], activity['type'],
                                   activity['date'], activity['quantity'], activity['fee'], activity['value'],
                                   activity['SymbolProfile']['currency'], activity['comment']])
            table = pretty_print_table(["ID", "NAME", "TYPE", "DATE", "QUANTITY",
                                        "FEE", "VALUE", "CURRENCY", "COMMENT"],
                                       table_data)
            logger.info("\n%s", table)
            logger.info("End of operation")
        elif operations[i] == DELETE_ALL_ACTS:
            logger.info("Starting delete")
            ghost.delete_all_acts()
            logger.info("End delete")
        else:
            logger.info("Unknown Operation")
