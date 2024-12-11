from ape import networks, accounts


def get_account():
    if networks.provider.network.name in ["mainnet-fork", "local"]:
        return accounts.test_accounts[0]
    else:
        return accounts.load("mymeta")
