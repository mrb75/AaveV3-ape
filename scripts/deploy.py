from ape import networks, accounts, project
from .helpers import get_account
import click
from ape.cli import ConnectedProviderCommand
from web3 import Web3


def main():
    account = get_account()
    pool = get_pool()
    weth = get_weth()
    [ecosystem_name, network_name, provider_name] = get_net_info()
    erc20_address = project.config.aave[ecosystem_name][network_name]["weth_token"]
    print(f"pool address : {pool}")
    print(f"weth address : {weth}")

    print("supply process started\n")
    supply_amount = project.config.values.borrow_amount
    approve_token(supply_amount,
                  pool.address, erc20_address, account.address)
    supply_tx = pool.supply(erc20_address, supply_amount,
                            account.address, 0, sender=account)
    print("supply process ended\n")
    get_borrowable_data(pool, account)
    print("borrow process started\n")
    borrow(supply_amount, pool, account)
    print("borrow process ended\n")
    get_borrowable_data(pool, account)
    print("repay process started\n")
    repay(pool, account)
    print("repay process ended\n")
    get_borrowable_data(pool, account)


def get_pool():
    account = get_account()
    dependency_project = project.dependencies["aave"]["1.19.4"]
    [ecosystem_name, network_name, provider_name] = get_net_info()
    provider_address = project.config.aave[ecosystem_name][network_name]["pool_address_provider"]
    provider = dependency_project.IPoolAddressesProvider.at(provider_address)
    return dependency_project.IPool.at(provider.getPool())


def get_weth():
    account = get_account()
    dependency_project = project.dependencies["aave"]["1.19.4"]
    [ecosystem_name, network_name, provider_name] = get_net_info()
    weth_address = project.config.aave[ecosystem_name][network_name]["weth_token"]
    weth = dependency_project.IWETH.at(weth_address)
    weth.deposit(sender=account, value=project.config.values.borrow_amount)
    return weth


def approve_token(amount, spender, address, account):
    dependency_project = project.dependencies["openzeppelin"]["4.8.0"]
    token = dependency_project.IERC20.at(address)
    tx = token.approve(spender, amount, sender=account)
    print("approved.")


def get_eth_price(amount, price_feed_address):
    dependency_project = project.dependencies["chainlink"]["2.18.0"]
    [ecosystem_name, network_name, provider_name] = get_net_info()
    aggregator = dependency_project.AggregatorV3Interface.at(
        price_feed_address)
    latest_price = Web3.from_wei(aggregator.latestRoundData()[1], "ether")
    print(f"The  price is {latest_price}")
    return float(latest_price)


def get_borrowable_data(pool, account):
    (totalCollateralBase,
     totalDebtBase,
     availableBorrowsBase,
     currentLiquidationThreshold,
     ltv,
     healthFactor) = pool.getUserAccountData(account)
    [ecosystem_name, network_name, provider_name] = get_net_info()
    price_oracle = get_price_oracle()
    asset_price = price_oracle.getAssetPrice(
        project.config.aave[ecosystem_name][network_name]["weth_token"])
    print(f"totalCollateralBase : {totalCollateralBase}\n")
    print(f"totalDebtBase : {totalDebtBase}\n")
    print(f"availableBorrowsBase : {availableBorrowsBase}\n")
    return [totalCollateralBase/asset_price, totalDebtBase/asset_price, availableBorrowsBase/asset_price]


def get_price_oracle():
    dependency_project = project.dependencies["aave"]["1.19.4"]
    [ecosystem_name, network_name, provider_name] = get_net_info()
    provider_address = project.config.aave[ecosystem_name][network_name]["pool_address_provider"]
    provider = dependency_project.IPoolAddressesProvider.at(provider_address)
    return dependency_project.IPriceOracle.at(provider.getPriceOracle())


def borrow(amount, pool, account):
    [ecosystem_name, network_name, provider_name] = get_net_info()
    price_feed_address = project.config.aave[ecosystem_name][network_name]["dai_eth_price_feed"]
    dai_eth_price = get_eth_price(amount, price_feed_address)
    [totalCollateralBase, totalDebtBase,
        availableBorrowsBase] = get_borrowable_data(pool, account)
    dai_amount = (1/dai_eth_price)*availableBorrowsBase*0.95
    borrow_tx = pool.borrow(
        project.config.aave[ecosystem_name][network_name]["dai_token"], Web3.to_wei(dai_amount, "ether"), 2, 0, account.address, sender=account)


def repay(pool, account):
    [ecosystem_name, network_name, provider_name] = get_net_info()
    eth_amount = get_borrowable_data(
        pool, account)[1]
    price_feed_address = project.config.aave[ecosystem_name][network_name]["dai_eth_price_feed"]
    dai_eth_price = get_eth_price(eth_amount, price_feed_address)
    dai_amount = (1/dai_eth_price)*eth_amount
    dai_token = project.config.aave[ecosystem_name][network_name]["dai_token"]
    approve_token(Web3.to_wei(dai_amount, "ether"),
                  pool.address, dai_token, account)
    pool.repay(dai_token, Web3.to_wei(dai_amount, "ether"),
               2, account, sender=account)


def get_net_info():
    ecosystem_name = networks.provider.network.ecosystem.name
    network_name = networks.provider.network.name
    provider_name = networks.provider.name
    return [ecosystem_name, network_name, provider_name]
