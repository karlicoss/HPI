To enable completion for the `hpi` command:

If you don't want to use the files here, you can do this when you launch your shell like:

```bash
eval "$(_HPI_COMPLETE=bash_source hpi)"  # in ~/.bashrc
eval "$(_HPI_COMPLETE=zsh_source hpi)"  # in ~/.zshrc
eval "$(_HPI_COMPLETE=fish_source hpi)"  # in ~/.config/fish/config.fish
```

That is slightly slower since its generating the completion code on the fly -- see [click docs](https://click.palletsprojects.com/en/8.0.x/shell-completion/#enabling-completion) for more info

To use the generated completion files in this repository, you need to source the file in `./bash`, `./zsh`, or `./fish` depending on your shell.

If you don't have HPI cloned locally, after installing `HPI` you can generate the file yourself using one of the commands above. For example, for `bash`: `_HPI_COMPLETE=bash_source hpi > ~/.config/hpi_bash_completion`, and then source it like `source ~/.config/hpi_bash_completion`

### bash

Put `source /path/to/hpi/repo/misc/completion/bash/_hpi` in your `~/.bashrc`

### zsh

You can either source the file:

`source /path/to/hpi/repo/misc/completion/zsh/_hpi`

..or add the directory to your `fpath` to load it lazily:

`fpath=("/path/to/hpi/repo/misc/completion/zsh/" "${fpath[@]}")` (Note: the directory, not the script `_hpi`)

If your zsh configuration doesn't automatically run `compinit`, after modifying your `fpath` you should:

`autoload -Uz compinit && compinit`

### fish

`cp ./fish/hpi.fish ~/.config/fish/completions/`, then restart your shell
