import argparse
import random
import collections

import torch
import numpy as np
import cosine_annealing_warmup

import data_loader.data_loaders as module_data
import model.loss as module_loss
import model.metric as module_metric
import model.model as module_arch
from parse_config import ConfigParser
from trainer import PreTrainer
from utils import prepare_device


# fix random seeds for reproducibility
def set_seed(radom_seed=42):
    torch.manual_seed(radom_seed)
    torch.cuda.manual_seed(radom_seed)
    torch.cuda.manual_seed_all(radom_seed)
    np.random.seed(radom_seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    random.seed(radom_seed)

def main(config):
    set_seed(config['seed'])
    logger = config.get_logger('train')

    # setup data_loader instances
    data_loader, valid_data_loader = config.init_obj('data_loader', module_data)
    valid_data_loader = data_loader.split_validation()

    # build model architecture, then print to console
    model = config.init_obj('arch', module_arch)
    logger.info(model)

    # prepare for (multi-device) GPU training
    device, device_ids = prepare_device(config['n_gpu'])
    model = model.to(device)
    if len(device_ids) > 1:
        model = torch.nn.DataParallel(model, device_ids=device_ids)

    # get function handles of loss and metrics
    criterion = None  # getattr(module_loss, config['loss'])
    metrics = None # [getattr(module_metric, met) for met in config['metrics']]

    # build optimizer, learning rate scheduler. delete every lines containing lr_scheduler for disabling scheduler
    trainable_params = filter(lambda p: p.requires_grad, model.parameters())
    optimizer = config.init_obj('optimizer', torch.optim, trainable_params)
    lr_scheduler = config.init_obj('lr_scheduler', cosine_annealing_warmup, optimizer) # use custom scheduler

    trainer = PreTrainer(model, criterion, metrics, optimizer,
                      config=config,
                      device=device,
                      data_loader=data_loader,
                      valid_data_loader=valid_data_loader,
                      lr_scheduler=lr_scheduler)
    trainer.train()


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='PyTorch Template')
    args.add_argument('-c', '--config', default=None, type=str,
                      help='config file path (default: None)')
    args.add_argument('-r', '--resume', default=None, type=str,
                      help='path to latest checkpoint (default: None)')
    args.add_argument('-d', '--device', default=None, type=str,
                      help='indices of GPUs to enable (default: all)')

    # custom cli options to modify configuration from default values given in json file.
    CustomArgs = collections.namedtuple('CustomArgs', 'flags type target')
    options = [
        CustomArgs(['--lr', '--learning_rate'], type=float, target='optimizer;args;lr'),
        CustomArgs(['--bs', '--batch_size'], type=int, target='data_loader;args;batch_size')
    ]
    config = ConfigParser.from_args(args, options)
    
    main(config)

    # class Config:
    #     # seed:int
    #     device:Literal['cpu','cuda']
    #     # data_path:str
    #     # val_ratio:float
    #     # batch_size:int
    #     # num_workers:int
    #     # num_epoch:int
    #     # learning_rate:int
    #     image_size:int
    #     patch_size:int
    #     mask_ratio:float
    #     encoder:Literal['ViT-S','ViT-B','ViT-L']
    #     dropout:float