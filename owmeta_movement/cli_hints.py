from owmeta_core.cli_common import METHOD_NAMED_ARG

CLI_HINTS = {
    'owmeta_movement.command.ZenodoCommand': {
        'list_files': {
            (METHOD_NAMED_ARG, 'zenodo_id'): {
                'names': ['zenodo_id'],
            },
        }
    },
    'owmeta_movement.command.CeMEECommand': {
        'save': {
            (METHOD_NAMED_ARG, 'zenodo_id'): {
                'names': ['zenodo_id'],
            },
            (METHOD_NAMED_ARG, 'zenodo_file_name'): {
                'names': ['zenodo_file_name'],
            },
            (METHOD_NAMED_ARG, 'sample_zip_file_name'): {
                'names': ['sample_zip_file_name'],
            },
        },
        'translate': {
            (METHOD_NAMED_ARG, 'data_source'): {
                'names': ['data_source'],
            },

        }
    },
}
