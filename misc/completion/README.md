To enable completion for the `hpi` command:

If you don't want to use the files here, you can do this when you launch your shell like:

```bash
eval "$(_HPI_COMPLETE=bash_source hpi)"  # in ~/.bashrc
eval "$(_HPI_COMPLETE=zsh_source hpi)"  # in ~/.zshrc
eval "$(_HPI_COMPLETE=fish_source hpi)"  # in ~/.config/fish/config.fish
```

That is slightly slower since its generating the completion code on the fly -- see [click docs](https://click.palletsprojects.com/en/8.0.x/shell-completion/#enabling-completion) for more info

To use the completions here:

### bash

Put `source /path/to/bash/_hpi` in your `~/.bashrc`

### zsh

You can either source the file:

`source /path/to/zsh/_hpi`

..or add the directory to your `fpath` to load it lazily:

`fpath=("/path/to/zsh/" "${fpath[@]}")` (Note: the directory, not the script `_hpi`)

If your zsh configuration doesn't automatically run `compinit`, after modifying your `fpath` you should:

`autoload -Uz compinit && compinit`

### fish

`cp ./fish/hpi.fish ~/.config/fish/completions/`, then restart your shell
