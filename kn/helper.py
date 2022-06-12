import json
import os
import shutil
import tempfile
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def copy_to_temp(org_path):
    path = os.path.join(tempfile.mkdtemp(), os.path.basename(org_path))
    shutil.copytree(org_path, path)
    return path


def get_yamls_from_dirpath(dirpath: Path) -> Tuple[List[Dict], List[Path]]:
    _yaml_objs, _filepaths = [], []
    for _path in Path(dirpath).rglob('*.yml'):
        with open(_path) as f:
            _yamls = list(yaml.safe_load_all(f.read()))
            _yaml_objs.extend(_yamls)
            _filepaths.extend([_path] * len(_yamls))
    return _yaml_objs, _filepaths


def update_yamls_on_disk(objs: Dict[Path, List[Dict]]):
    for path, config in objs.items():
        with open(path, 'w') as f:
            f.writelines(yaml.dump_all(config))


def change_to_kn_service(
    path: Path, concurrency, min_replicas, max_replicas
) -> Dict[Path, List[Dict]]:
    _temp_objs = defaultdict(list)
    _org_objs, _org_paths = get_yamls_from_dirpath(path)
    for _obj, _path in zip(_org_objs, _org_paths):
        if _obj['kind'] == 'Service':
            continue
        elif _obj['kind'] == 'Deployment':
            _new_obj = deepcopy(_obj)
            _new_obj['apiVersion'] = 'serving.knative.dev/v1'
            _new_obj['kind'] = 'Service'
            del _new_obj['spec']['template']['spec']['containers'][0]['env'][0]
            for _field in ('replicas', 'strategy', 'selector'):
                del _new_obj['spec'][_field]

            if is_gateway(_new_obj['spec']['template']['metadata']['labels']):
                patch_deployments_addresses(_new_obj)
                if is_http2(
                    _new_obj['spec']['template']['spec']['containers'][0]['args']
                ):
                    patch_h2c(_new_obj)
            else:
                # required for gRPC calls for all Executors
                patch_h2c(_new_obj)

            patch_kn_annotations(_new_obj, concurrency, min_replicas, max_replicas)

            _temp_objs[_path].append(_new_obj)
        else:
            _temp_objs[_path].append(_obj)

    update_yamls_on_disk(_temp_objs)
    return _temp_objs


def is_gateway(labels: Dict) -> bool:
    return labels.get('pod_type', 'WORKER') == 'GATEWAY'


def is_http2(args: List[str]) -> bool:
    try:
        _index = args.index('--protocol')
        return args[_index + 1].upper() in ('GRPC', 'WEBSOCKET')
    except ValueError:
        # if `--protocol` param doesn't exist, it is GRPC
        return True


def patch_h2c(obj):
    obj['spec']['template']['spec']['containers'][0]['ports'][0] = {
        'name': 'h2c',
        'containerPort': 8080,
    }


def patch_deployments_addresses(obj: List[str]):
    _args = obj['spec']['template']['spec']['containers'][0]['args']
    _index = _args.index('--deployments-addresses')
    _addresses: Dict = json.loads(_args[_index + 1])
    _new_addresses = {}
    for k, v in _addresses.items():
        _new_addresses[k] = [i.replace('8080', '80') for i in v]

    _new_args: List = (
        _args[: _index + 1] + [json.dumps(_new_addresses)] + _args[_index + 2 :]
    )
    obj['spec']['template']['spec']['containers'][0]['args'] = _new_args


def patch_kn_annotations(obj, concurrency, min_replicas, max_replicas):
    _annotations = {
        'autoscaling.knative.dev/metric': 'concurrency',
        'autoscaling.knative.dev/target': str(concurrency),
        'autoscaling.knative.dev/min-scale': str(min_replicas),
        'autoscaling.knative.dev/max-scale': str(max_replicas),
    }
    obj['spec']['template']['metadata']['annotations'].update(_annotations)
