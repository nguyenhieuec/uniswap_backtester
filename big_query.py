import os
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account


class UniswapV3Data:
    def __init__(self, path, project_id, key_path) -> None:
        credentials = service_account.Credentials.from_service_account_file(key_path)
        self.client = bigquery.Client(credentials=credentials, project=project_id)
        self.default_dir = path

    def get_swap_data(self, address, download_latest=False):
        # check if file already exists 
        files = os.listdir(self.default_dir)
        end_block = 0
        current_block = 0
        for file in files:
            if address in file:
                _, _, current_block = file.split('-')
                current_block = int(current_block[:-4])
                end_block = max(current_block, end_block)
        
        if download_latest:
            # if yes download from the last snap shot
            swap_query = f"""
                select * from `blockchain-etl.ethereum_uniswap.UniswapV3Pool_event_Swap`
                where contract_address='{address}' and block_number > {end_block}
                order by block_number;
                """ if end_block else f"""
                select * from `blockchain-etl.ethereum_uniswap.UniswapV3Pool_event_Swap`
                where contract_address='{address}'
                order by block_number;
                """
            query_job = self.client.query(swap_query)
            output = query_job.result().to_dataframe()
            output.to_csv(f'{self.default_dir}/{address}-{output.block_number.iloc[0]}-{output.block_number.iloc[-1]}.csv', index=False)
    
        # check if directory again exists 
        files = os.listdir(self.default_dir)
        swap_data_list = []
        for file in files:
            if address in file:
                swap_data_list.append(pd.read_csv(os.path.join(self.default_dir, file)))
        
        return pd.concat(swap_data_list)
    
    def get_gas_data(self, start_block, end_block, save=True):
        file_name = f'{self.default_dir}/gas-{start_block}-{end_block}.csv'
        if file_name in os.listdir(self.default_dir):
            return pd.read_csv(file_name)
        else:
            # query the data
            gas_query = f"""
                select avg(gas_price) as gas_price, block_number from `bigquery-public-data.crypto_ethereum.transactions` 
                where block_number>={start_block} and block_number <{end_block}
                group by block_number
                order by block_number desc;
                """
            query_job = self.client.query(gas_query)
            output = query_job.result().to_dataframe()
            output.to_csv(file_name, index=False)
            return output