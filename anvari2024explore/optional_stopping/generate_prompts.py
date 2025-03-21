import os
import sys
import pandas as pd
import jsonlines

# Set project root if needed for imports (adjust path as necessary)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load data from two CSV files (do not include original data files in repository)
script_dir = os.path.dirname(os.path.abspath(__file__))
file1 = os.path.join(script_dir, "optional_stopping_2023-04-28_out.csv")
file2 = os.path.join(script_dir, "optional_stopping_2023-06-02_out.csv")
df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)
df_all = pd.concat([df1, df2], ignore_index=True)

# Group the data by participant and session
groups = df_all.groupby(["participant.code", "session.code"])

# Fixed instructions text for the Optional Stopping Task with Recall
instructions = (
    "In each block of this task, you will search for rewards among 20 different boxes. "
    "You can open a box by clicking on it, which reveals how much it's worth. Each box has a randomly determined value between 0 and 10. "
    "However, every time you open a box you pay a cost ranging from 0.05 to 0.4 points depending on the block you are in.\n\n"
    "After opening a box, you can either settle on the highest value among the opened boxes—thereby ending that block—or keep opening more boxes (up to a maximum of 20).\n\n"
    "The costs for opening boxes, as well as the rewards, change from one block to the next. At the end of each block, "
    "you will receive the highest value you have discovered minus the total cost incurred from opening boxes.\n\n"
    "The first block is for practice, but the earnings of the remaining 8 blocks will be added up and used to calculate your bonus. "
    "For this task, you will be paid a bonus of 2 pence (£0.02) per point.\n\n"
    "Note: You can recall the best option encountered so far when deciding to stop."
)

all_prompts = []

# Process each experimental session
for (participant_code, session_code), df_session in groups:
    # Sort trials by block then by trial number
    df_session = df_session.sort_values(by=["block", "trial"])
    
    # Begin building the prompt text with instructions
    prompt_text = instructions + "\n\n"
    
    # Iterate over each unique block (Block 1: Practice; Blocks 2-9: Incentivized)
    blocks = sorted(df_session["block"].unique())
    for block in blocks:
        df_block = df_session[df_session["block"] == block]
        # For incentivized blocks, also display the cost per box (assumed constant in the block)
        if block == 1:
            prompt_text += "Practice Block:\n\n"
        else:
            cost_per_box = df_block.iloc[0]["player.cost_order"]
            prompt_text += f"Incentivized Block {block - 1} (Cost per box: {cost_per_box} points):\n\n"
        
        # Iterate over trials in the block
        for i, (_, row) in enumerate(df_block.iterrows()):
            trial_num = int(row["trial"])
            chest_selection = row["player.chest_selection"]
            chest_payoff = row["player.chest_payoff"]
            accumulated_cost = row["player.accumulated_cost"]
            current_best = row["player.current_best_payoff"]
            
            # Build trial description
            trial_line = (
                f"Trial {trial_num}: You opened box <<{chest_selection}>> revealing {chest_payoff} points. "
                f"Current best: {current_best} points. Accumulated cost: {accumulated_cost} points.\n"
            )
            prompt_text += trial_line
        
        prompt_text += "\n"
    
    prompt_text += "End of session.\n"
    
    # Construct the prompt dictionary for one session
    prompt_dict = {
        "text": prompt_text,
        "experiment": "optional_stopping_with_recall",
        "participant": participant_code,
        "session": session_code
    }
    all_prompts.append(prompt_dict)

# Write all prompts to a JSONL file
output_file = os.path.join(script_dir, "prompts.jsonl")
with jsonlines.open(output_file, mode='w') as writer:
    writer.write_all(all_prompts)

print(f"Created {len(all_prompts)} prompt(s) in {output_file}.")
