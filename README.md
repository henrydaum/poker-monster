# Poker Monster
## *Strategy Card Game and AI Project* <mark>by Henry Daum with art by Charlotte Daum</mark>

---

This repository contains the code for a fully functional web game with an AI opponent (screenshots & video below). I designed the game myself, and started it about two years ago. The AI opponent is good enough to beat me at my own game, although it still has room for improvement. It is a reinforcement learning model made with PyTorch code and trained over 30,000 games. The website design was done in HTML/CSS, and the backend code was ported using Flask. I deployed the game using Render onto poker.henrydaum.site, but I took it down and it redirects here now.

On this repository, within its version history, you can find code about:
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
- many different sizes of networks ranging from ~10,000 to ~500,000,000 parameters
- in addition to reinforcement learning, supervised learning on minimax results
- various complicated training programs
- actor-critic models (tried numerous times)
- world models
- Other things I am forgetting

The game engine uses mostly classical Python with no imported libraries to speak of, done mostly with four nested Classes. Each card and action type was given a specific subclass.

Before making the game into code, it was a physical card game. The game theory behind the game carefully balances attrition and tempo strategies, with the two decks having roughly equal winrates despite using vastly different strategies (not easy).

Lastly, the game includes a full set of art by my sister, Charlotte Daum.

---

## Screenshots/Video:
<img width="2557" height="1259" alt="Screenshot 2025-10-13 204533" src="https://github.com/user-attachments/assets/aa681b80-cafc-48c3-abce-b5646a2873e8" />
<img width="2556" height="1259" alt="Screenshot 2025-10-13 204619" src="https://github.com/user-attachments/assets/c0d69535-990f-4433-bbc1-25ba9aa3b289" />


https://github.com/user-attachments/assets/1bce15db-fb6d-4663-8dda-0347b4e3f202

### Example Training Graph:
<img width="330" height="330" alt="PokerMonsterTrainingCurves" src="https://github.com/user-attachments/assets/e7265657-00bd-4711-827d-0b2dde39c777" />

