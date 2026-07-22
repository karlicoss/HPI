-- This filter is loaded only by _quarto-preview.yml.
-- It never runs during normal rendering or `tox -e quarto`.
--
-- The canonical render produces GFM, so links in QMD sources target the generated .md files.
-- Quarto website previews preserve those .md targets instead of resolving them to the corresponding website .html pages.
-- Linking to .qmd is not an option because Quarto preserves that extension in generated GFM, which would break the GitHub-facing documentation.
--
-- Rewrite a .md link only when a corresponding .qmd source exists.
-- This leaves hand-written Markdown such as QUERY.md and DENYLIST.md unchanged.
local function file_exists(path)
  local file = io.open(path, "r")
  if file == nil then
    return false
  end
  file:close()
  return true
end

function Link(link)
  local path, fragment = link.target:match("^([^#]+)(#.*)$")
  if path == nil then
    path = link.target
    fragment = ""
  end

  if not path:match("%.md$") then
    return nil
  end

  local qmd = path:gsub("%.md$", ".qmd")
  local source_dir = pandoc.path.directory(quarto.doc.input_file)
  if not file_exists(pandoc.path.join({ source_dir, qmd })) then
    return nil
  end

  link.target = qmd:gsub("%.qmd$", ".html") .. fragment
  return link
end
