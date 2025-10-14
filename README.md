# Poker Monster
## *Strategy Card Game and AI Attempt* <mark>by Henry Daum with art by Charlotte Daum</mark>

---

Although this website once hosted a web game, it is no longer live and redirects here — I took it down after realizing I’d spent literally countless hours building, breaking, and rebuilding it to no avail. Everything I learned about reinforcement learning (with PyTorch), tree search, Flask deployment, HTML web design, and game theory can be found here. I tried many different approaches that can be traced to different versions. Specifically, I tried:
- minimax
- Monte-Carlo tree search (MCTS)
- alpha/beta pruning
- recurrent neural networks (RNNs)
- long-short term memory networks (LSTMs)
- gated recurrent units (GRUs)
- transformers
- feedforward networks
- population training
- various kinds of training loops
- random opponents
- REINFORCE (-log(prob)*R) with sampling
- reward shaping with different gammas (discount factors) for different kinds of rewards
- training on 30,000 games
- cosine annealing learning rate scheduler
- entropy
- entropy annealing
- temperature annealing
- training by allowing AIs to "predict" what their opponents were doing during their turns
- various kinds of input vector functions of various sizes
- many different sizes of networks ranging from 10,000s to 500,000,000 parameters
- in addition to reinforcement learning, supervised learning on minimax results
- various complicated training programs
- Other things I am forgetting

The game engine uses mostly classical Python with no imported libraries to speak of, done mostly with four nested Classes. Each card and action was given a specific subclass.

The game theory behind the game carefully balances attrition and tempo strategies, and has a nearly 50% winrate for each deck despite the two using vastly different strategies.

Lastly, the game includes a full set of art by my sister, Charlotte Daum.

I'm not one for platitudes, but this thing really is a Monster.

---

## Images:
<img width="2557" height="1259" alt="Screenshot 2025-10-13 204533" src="https://github.com/user-attachments/assets/aa681b80-cafc-48c3-abce-b5646a2873e8" />
<img width="2556" height="1259" alt="Screenshot 2025-10-13 204619" src="https://github.com/user-attachments/assets/c0d69535-990f-4433-bbc1-25ba9aa3b289" />
