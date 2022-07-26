# https://www.enterprisedb.com/postgres-tutorials/introduction-postgresql-performance-tuning-and-optimization

import multiprocessing
import os
import math


class ConfigOptimizer:
    def __init__(self):
        self.__input_file_name = 'postgresql.conf'
        self.__output_file_name = f'{self.__input_file_name}.optimized'
        self.__keys_to_tune = {
            # ------------------------------------------
            'huge_pages': 'on',
            # ------------------------------------------
            'wal_recycle': 'off',
            # ------------------------------------------
            'wal_init_zero': 'off',
            # ------------------------------------------
            'work_mem': '64MB',
            # ------------------------------------------
            'maintenance_work_mem': '1GB',
            # ------------------------------------------
            'autovacuum_work_mem': '64MB',
            # ------------------------------------------
            'effective_io_concurrency': '200',
            # ------------------------------------------
            'wal_compression': 'on',
            # ------------------------------------------
            'wal_log_hints': 'on',
            # ------------------------------------------
            'wal_buffers': '64MB',
            # ------------------------------------------
            'checkpoint_timeout': '15min',
            # ------------------------------------------
            'checkpoint_completion_target': '0.9',
            # ------------------------------------------
            'archive_mode': 'on',
            # ------------------------------------------
            'cpu_tuple_cost': '0.03',
            # ------------------------------------------
            'logging_collector': 'on',
            # ------------------------------------------
            'log_directory': '\'log\'',
            # TODO If the logging_collector is on, this should be set to a location outside of the data directory.
            #  This way the logs are not part of base backups.
            # ------------------------------------------
            'log_checkpoints': 'on',
            # ------------------------------------------
            'log_line_prefix': '\'%m [%p-%l] %u@%d app=%a \'',
            # ------------------------------------------
            'log_lock_waits': 'on',
            # ------------------------------------------
            'log_statement': '\'ddl\'',
            # ------------------------------------------
            'log_temp_files': '0',
            # ------------------------------------------
            'log_autovacuum_min_duration': '0',
            # ------------------------------------------
            'autovacuum_max_workers': '5',
            # ------------------------------------------
            'autovacuum_vacuum_cost_limit': '3000',
            # ------------------------------------------
            'idle_in_transaction_session_timeout': '10min',
            # ------------------------------------------
            'lc_messages': '\'C\'',
            # ------------------------------------------
            # 'shared_preload_libraries': '\'pg_stat_statements\'',
            # ------------------------------------------
            'listen_addresses': '\'*\'',
        }
        self.__cpu_cores_count = None
        self.__ram_in_bytes = None
        self.__disk_in_bytes = None
        self.__is_hdd_disk = None
        self.__init_machine_specific_key()

    def __init_machine_specific_key(self):
        self.__init_cpu_cores_count()
        self.__init_ram_in_bytes()
        self.__init_disk_in_bytes()
        self.__init_is_hdd_disk()
        self.__keys_to_tune['max_connections'] = str(max(4 * self.__cpu_cores_count, 100))
        self.__keys_to_tune['shared_buffers'] = str(
            min(math.floor(self.__ram_in_bytes / (2 * 1024 ** 3)), 10)) + 'GB'  # LEAST(RAM/2, 10GB)
        self.__keys_to_tune['max_wal_size'] = str(
            max(math.floor(self.__disk_in_bytes / (2 * 1024 ** 3)), 10)) + 'GB'  # MAX(DISK/2, 10GB)
        self.__keys_to_tune['random_page_cost'] = '4.0' if self.__is_hdd_disk else '1.1'
        self.__keys_to_tune['effective_cache_size'] = str(math.floor((0.75 * self.__ram_in_bytes) / (1024 ** 3))) + 'GB'

    def __init_cpu_cores_count(self):
        self.__cpu_cores_count = multiprocessing.cpu_count()

    def __init_ram_in_bytes(self):
        self.__ram_in_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')

    def __init_disk_in_bytes(self):
        statvfs = os.statvfs('/')
        self.__disk_in_bytes = statvfs.f_frsize * statvfs.f_blocks

    def __init_is_hdd_disk(self):
        stream = os.popen('cat /sys/block/sda/queue/rotational')
        output = stream.read()[0]
        self.__is_hdd_disk = True if output == '1' else False

    def run(self):
        with open(self.__input_file_name) as input_file:
            lines = input_file.readlines()
        output_lines = []
        for line in lines:
            if line == '\n' or line.lstrip().startswith('#'):
                continue
            comment_index = line.rstrip().find('#')
            comment_index = comment_index if comment_index != -1 else len(line)
            new_line = line[:comment_index].rstrip()
            key, value = new_line.split('=')
            key = key.strip()
            value = value.strip()
            # TODO: check duplicate keys in config
            if key in self.__keys_to_tune:
                new_line = f'{key} = {self.__keys_to_tune[key]} # MODIFIED'
                del self.__keys_to_tune[key]
            output_lines.append(new_line)
        output_lines.append('########################################################################')
        output_lines.append('# Values not in original config')
        output_lines.append('########################################################################')
        for key, value in self.__keys_to_tune.items():
            output_lines.append(f'{key} = {self.__keys_to_tune[key]}')
        with open(self.__output_file_name, 'w') as output_file:
            output_file.write('\n'.join(output_lines))


if __name__ == '__main__':
    configOptimizer = ConfigOptimizer()
    configOptimizer.run()
