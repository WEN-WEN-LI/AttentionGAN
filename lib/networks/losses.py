import numpy as np

import torch
import torch.nn as nn


class PointFlowNLL(nn.Module):
    def __init__(self):
        super(PointFlowNLL, self).__init__()

    def forward(self, samples, mus, logvars):
        return 0.5 * torch.add(
            torch.sum(sum(logvars) + ((samples[0] - mus[0])**2 / torch.exp(logvars[0]))) / samples[0].shape[0],
            np.log(2.0 * np.pi) * samples[0].shape[1] * samples[0].shape[2]
        )


class GaussianFlowNLL(nn.Module):
    def __init__(self):
        super(GaussianFlowNLL, self).__init__()

    def forward(self, samples, mus, logvars):
        return 0.5 * torch.add(
            torch.sum(sum(logvars) + ((samples[0] - mus[0])**2 / torch.exp(logvars[0]))) / samples[0].shape[0],
            np.log(2.0 * np.pi) * samples[0].shape[1]
        )


class GaussianEntropy(nn.Module):
    def __init__(self):
        super(GaussianEntropy, self).__init__()

    def forward(self, logvars):
        return 0.5 * torch.add(logvars.shape[1] * (1.0 + np.log(2.0 * np.pi)), logvars.sum(1).mean())


class Local_Cond_RNVP_MC_Global_RNVP_VAE_Loss(nn.Module):
    def __init__(self, **kwargs):
        super(Local_Cond_RNVP_MC_Global_RNVP_VAE_Loss, self).__init__()
        self.pnll_weight = kwargs.get('pnll_weight')
        self.gnll_weight = kwargs.get('gnll_weight')
        self.gent_weight = kwargs.get('gent_weight')
        self.PNLL = PointFlowNLL()
        self.GNLL = GaussianFlowNLL()
        self.GENT = GaussianEntropy()

    def forward(self, g_clouds, l_clouds, outputs):
        pnll = self.PNLL(outputs['p_prior_samples'], outputs['p_prior_mus'], outputs['p_prior_logvars'])
        gnll = self.GNLL(outputs['g_prior_samples'], outputs['g_prior_mus'], outputs['g_prior_logvars'])
        gent = self.GENT(outputs['g_posterior_logvars'])
        return self.pnll_weight * pnll + self.gnll_weight * gnll - self.gent_weight * gent, pnll, gnll, gent


class GAN_Loss(nn.Module):
    def __init__(self):
        super(GAN_Loss, self).__init__()

    def forward(self, i_gt, i_pred, isList=False):
        if not isList:
            ld = torch.square(i_gt - 1) + torch.square(i_pred - 0) # (16, 1)
            lg = torch.square(i_pred - 1) # (16, 1)
            sum1 = torch.mean(0.5 * ld + 0.5 * lg)
            return sum1
        if isList:
            ld = 0
            lg = 0
            for i in range(len(i_gt)):
                ld += torch.square(i_gt[i] - 1) + torch.square(i_pred[i] - 0)
                lg += torch.square(i_pred[i] - 1)
            sum2 = torch.mean(0.5 * ld + 0.5 * lg)/len(i_gt)
            return sum2
