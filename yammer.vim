if !has('python')
	s:ErrMsg( "Error: Required vim compiled with +python" )
	finish
endif



function! s:YammerShow()
python << endpython
import vim, sys, os
sys.path.append(os.path.expanduser("~/.vim/plugin"))
import yammer

y = yammer.Yammer()
mf = yammer.MessageFormatter()

# split buffers
vim.command("new")

mp = yammer.MessageParser()
messages = mp.read(y.messages())

s = mf.format(messages)
l = s.split("\n")
vim.current.buffer[0] = str(l[0])
for line in l[1:]:
    vim.current.buffer.append(str(line))
endpython
endfunction




function! s:YammerPost()
python << endpython
import vim

import vim, sys, os
sys.path.append(os.path.expanduser("~/.vim/plugin"))
import yammer

y = yammer.Yammer()
y.post(vim.current.range[0])

endpython
endfunction





if !exists(":YammerShow")
    command YammerShow :call s:YammerShow()
endif

if !exists(":YammerPost")
    command YammerPost :call s:YammerPost()
endif

