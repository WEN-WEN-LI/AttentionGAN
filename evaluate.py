import argparse
import os
import io
import yaml

import torch
from torch.utils.data import DataLoader

from lib.datasets.datasets import ShapeNetCoreDataset, ShapeNetAllDataset
from lib.datasets.image_transformations import ComposeImageTransformation
from lib.datasets.cloud_transformations import ComposeCloudTransformation

from lib.networks.models import Local_Cond_RNVP_MC_Global_RNVP_VAE, Local_Cond_RNVP_MC_Global_RNVP_VAE_IC
from lib.networks.losses import Local_Cond_RNVP_MC_Global_RNVP_VAE_Loss
from lib.networks.evaluating import evaluate


def define_options_parser():
    parser = argparse.ArgumentParser(description='Model training script. Provide a suitable config.')
    parser.add_argument('config', type=str, help='Path to config file in YAML format.')
    parser.add_argument('modelname', type=str, help='Model name to save checkpoints.')
    parser.add_argument('part', help='Part of dataset (train / val / test).')
    parser.add_argument('cloud_size', type=int, help='Number of input points.')
    parser.add_argument('sampled_cloud_size', type=int, help='Number of sampled points.')
    parser.add_argument('mode', type=str, help='Prediction mode (training / evaluating / generating / predicting).')
    parser.add_argument('--orig_scale_evaluation', action='store_true',
                        help='Evaluation in original per cloud scale flag.')
    parser.add_argument('--save', action='store_true', help='Saving flag.')
    return parser


parser = define_options_parser()
args = parser.parse_args()
with io.open(args.config, 'r') as stream:
    config = yaml.full_load(stream)
config['model_name'] = '{0}.pkl'.format(args.modelname)
config['part'] = args.part
config['cloud_size'] = args.cloud_size
config['sampled_cloud_size'] = args.sampled_cloud_size
config['util_mode'] = args.mode
config['orig_scale_evaluation'] = True if args.orig_scale_evaluation else False
config['unit_scale_evaluation'] = True #if args.unit_scale_evaluation else False
config['saving'] = True #if args.save else False
config['N_sets'] = 1
config['cd'] = True
config['emd'] = True
config['f1'] = True
print('Configurations loaded.')

if config['train_mode'] == 'p_rnvp_mc_g_rnvp_vae':
    cloud_transform = ComposeCloudTransformation(**config)
    eval_dataset = ShapeNetCoreDataset(config['path2data'],
                                       part=args.part, meshes_fname=config['meshes_fname'],
                                       cloud_size=config['cloud_size'], return_eval_cloud=True,
                                       return_original_scale=config['cloud_rescale2orig'] or config['orig_scale_evaluation'],
                                       cloud_transform=cloud_transform,
                                       chosen_label=config['chosen_label'])
elif config['train_mode'] == 'p_rnvp_mc_g_rnvp_vae_ic':
    image_transform = ComposeImageTransformation(**config)
    cloud_transform = ComposeCloudTransformation(**config)
    eval_dataset = ShapeNetAllDataset(config['path2data'], part=args.part,
                                       images_fname=config['images_fname'], meshes_fname=config['meshes_fname'],
                                       cloud_size=config['cloud_size'], return_eval_cloud=True,
                                       return_original_scale=config['cloud_rescale2orig'] or config['orig_scale_evaluation'],
                                       image_transform=image_transform, cloud_transform=cloud_transform,
                                       chosen_label=config['chosen_label'])

print('Dataset init: done.')

eval_iterator = DataLoader(eval_dataset, batch_size=config['batch_size'], shuffle=False,
                           num_workers=config['num_workers'], pin_memory=True, drop_last=False)
print('Iterator init: done.')

if config['train_mode'] == 'p_rnvp_mc_g_rnvp_vae':
    model = Local_Cond_RNVP_MC_Global_RNVP_VAE(**config).cuda()
elif config['train_mode'] == 'p_rnvp_mc_g_rnvp_vae_ic':
    model = Local_Cond_RNVP_MC_Global_RNVP_VAE_IC(**config).cuda()
print('Model init: done.')

if config['util_mode'] == 'training':
    criterion = Local_Cond_RNVP_MC_Global_RNVP_VAE_Loss(**config).cuda()
else:
    criterion = None
print('Loss init: done.')

path2checkpoint = os.path.join(config['path2save'], 'models', config['model_name'])
checkpoint = torch.load(path2checkpoint)
model.load_state_dict(checkpoint['model_state'])
epoch = checkpoint['epoch']
print("epoch: ", epoch)
del(checkpoint)
print('Model {} loaded.'.format(path2checkpoint))

if config['util_mode'] == 'reconstruction':
    res = evaluate(eval_iterator, model, criterion, **config)
    # evaluate(eval_iterator, **config)
    print('CD:', res[0])
    print('EMD:', res[1])
    print('f1:', res[2])
