'''
plot actions and gt_actions
'''
import os
import matplotlib.pyplot as plt
import torch

result_dir = './results/test_infer'

data = torch.load(os.path.join(result_dir, "actions_data.pt"), map_location='cpu')
actions = data["actions"]
gt_actions = data["gt_actions"]

action_dim = 8

fig, axs = plt.subplots(action_dim, 1, figsize=(10, 10))

for i in range(action_dim):
    axs[i].plot(actions[:, i].cpu().detach().numpy(), label="pred")
    axs[i].plot(gt_actions[:, i].cpu().detach().numpy(), label="gt")
    axs[i].legend()
plt.show()