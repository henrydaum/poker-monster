from flask import Flask, render_template, redirect, url_for, session
# Import information needed to rewrite run_game() for a server
from poker_monster import build_decks, Player, GameState, create_action, hyperparameters, Network

# Need to store the gamestate and the previous AI hidden state in the session (like a cache)
# The session can't hold the gamestate directly, must convert all information to and from dicts

app = Flask(__name__)
# A secret key is required to use sessions
app.secret_key = 'a_very_secret_key'

hyperparameters = {
    # Network architecture:
    "lstm_size": 70,
    "num_lstm_layers": 3,  # Ignore dropout warning if X=1
    "feedforward_size": 70,
    # Reward shaping:
    "long_term_gamma": 0.95,  # Lower values decay the end-of-game reward to earlier turns faster
    "short_term_gamma": 0.75,
    "negative_reward_clamp": float('-inf'),  # Clamp negative rewards to this value to make them less punishing. All rewards below this value are set to this value (set to float('-inf') to disable)
    # Learning rate parameters (LR scheduler):
    "lr":1e-3,  # For 5 or more epochs, use 1e-4; for 1 epoch use 1e-3 (no scheduler)
    "use_lr_scheduler": True,  # lr scheduler (cosine annealing)
    "T_0": 250,  # lr cosine anneal period (repeats every X games with warm restarts)
    "T_mult": 1,  # Multiply T_0 by this factor every time it restarts (default is 1)
    "eta_min": 1e-5,  # Anneal from lr (above) to this lr
    # Misc. Parameters:
    "dropout_rate": 0.2,  # Randomly disables X% neurons during forward pass. Reduces overfitting, but too high a value adds a lot of noise to the loss.
    "weight_decay": 0.01,  # This is L2 regularization, adds a term to the loss calculation that punishes large weights
    "epochs": 1,  # 1 epoch is much faster than multiple because the torch gradient isn't recomputed
    "temperature": 2,  # Adds a degree of randomness to sample_action. Lower values are deterministic, higher values are random.
    "entropy_coef": 0.025,  # Higher values slow down learning, increase exploration, and slow convergence.
}

# Load AIs
hero_ai = Network(name="hero", **hyperparameters)
monster_ai = Network(name="monster", **hyperparameters)
try:
    hero_ai.load("hero")
except:
    print("No hero_ai to load")
try:
    monster_ai.load("monster")
except:
    print("No monster_ai to load")

def take_ai_turn(gs):
    while gs.me.player_type.startswith("computer_ai"):
        # AI takes turns until it is the user's turn
        if gs.me.name == "hero":
            choice_number, hidden state = hero_ai.sample_action(gs, training=False)
        elif gs.me.name == "monster":
            choice_number, hidden state = monster_ai.sample_action(gs, training=False)
        action = create_action(gs, choice_number)
        action.enact()

@app.route("/")
def index():
    """Initial route to start a new game."""
    # Need to somehow ask user if they want to play Hero or Monster
    user_choice = "hero"
    if user_choice == "hero":
        hero_player_type == "person"
        monster_player_type == "computer_ai"
    else:
        hero_player_type == "computer_ai"
        monster_player_type == "person"

    # Build decks and create player instances
    hero_deck, monster_deck = build_decks()
    hero = Player("hero", hero_deck, hero_player_type)
    monster = Player("monster", monster_deck, monster_player_type)

    # coin flip to see who goes first
    coin_flip = randint(0, 1)
    going_first = None
    if coin_flip == 0:  # Heads is for Monster, obviously
        going_first = "monster"
        monster.going_first = True
    else:
        going_first = "hero"
        hero.going_first = True
    
    # Create and configure the initial game state
    gs = GameState(hero, monster, turn_priority=going_first)
    gs.hero.shuffle()
    gs.monster.shuffle()
    gs.hero.draw(4)
    gs.monster.draw(4)

    # Initialize AI hidden state
    session['hidden_state'] = 
    
    # If the AI is going first, go ahead and take its turn
    if gs.me.player_type.startswith("computer_ai"):
        take_ai_turn(gs)

    # Store the game state object in the session
    session['gs'] = gs.to_dict() # You'll need to add a to_dict() method

    return redirect(url_for('display_gamestate'))

# Turns gamestate into HTML
@app.route("/gamestate")
def display_gamestate():
    """Displays the gamestate and possible actions."""
    # Load game state from the session
    if 'gs' not in session:
        return redirect(url_for('index'))

    gs = GameState.from_dict(session['gs']) # You'll need a from_dict() method

    # Check for a winner
    if gs.winner:
        return render_template('winner.html', winner=gs.winner)  # Separate winner page with option to restart

    return render_template('game.html', info=game_info, actions=available_actions)

# Turns HTML into an action
@app.route("/action/<int:action_id>")
def do_action(action_id):
    """Changes the gamestate based on the user's actions and takes the AI's turn."""
    if 'gs' not in session:
        return redirect(url_for('index'))
    
    gs = GameState.from_dict(session['gs'])

    # Create and execute the action
    action = create_action(gs, action_id)
    legal, reason = action.is_legal()
    
    if legal:
        action.enact()
        # This part of your logic might need adjustment for a web interface
    else:
        # Optionally, you can pass an error message to the user
        session['error_message'] = reason
    
    # If it's the AI's turn:
    if gs.me.player_type.startswith("computer_ai"):
        take_ai_turn(gs)

    # Save the updated game state back to the session
    session['gs'] = gs.to_dict()
    
    return redirect(url_for('display_gamestate'))

if __name__ == "__main__":
    app.run(debug=True)