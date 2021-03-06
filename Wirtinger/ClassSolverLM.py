#!/usr/bin/env python
"""
killMS, a package for calibration in radio interferometry.
Copyright (C) 2013-2017  Cyril Tasse, l'Observatoire de Paris,
SKA South Africa, Rhodes University

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import numpy as np
from killMS.Array import NpShared
from killMS.Predict.PredictGaussPoints_NumExpr5 import ClassPredict
import os
from killMS.Data import ClassVisServer
#from Sky import ClassSM
from killMS.Array import ModLinAlg
from killMS.Other import ClassTimeIt
from killMS.Array.Dot import NpDotSSE
from killMS.Wirtinger.ClassJacobianAntenna import ClassJacobianAntenna

class ClassSolverLM(ClassJacobianAntenna):
    def __init__(self, *args, **kwargs):
        ClassJacobianAntenna.__init__(self, *args, **kwargs)

    def PrepareJHJ_LM(self):

        self.L_JHJinv=[]
        if self.DataAllFlagged:
            return

        for ipol in range(self.NJacobBlocks_X):

            M=self.L_JHJ[ipol]
            if self.DoTikhonov:
                self.LambdaTkNorm=self.LambdaTk*np.mean(np.abs(np.diag(M)))
                
                # Lin.shape= (self.NDir,self.NJacobBlocks_X,self.NJacobBlocks_Y)
                Linv=np.diag(self.Linv[:,ipol,:].ravel())
                Linv*=self.LambdaTkNorm/(1.+self.LambdaLM)
                M2=M+Linv

                # pylab.clf()
                # pylab.subplot(1,2,1)
                # pylab.imshow(np.abs(M),interpolation="nearest")
                # pylab.colorbar()
                # pylab.subplot(1,2,2)
                # pylab.imshow(np.abs(Linv),interpolation="nearest")
                # pylab.colorbar()
                # pylab.draw()
                # pylab.show(False)
                # pylab.pause(0.1)
                # stop

            else:
                M2=M


            JHJinv=ModLinAlg.invSVD(M2)
            #JHJinv=ModLinAlg.invSVD(self.JHJ)
            self.L_JHJinv.append(JHJinv)

    def doLMStep(self,Gains):
            
        
        T=ClassTimeIt.ClassTimeIt("doLMStep")
        T.disable()

#         A=np.random.randn(10000,100)+1j*np.random.randn(10000,100)
#         B=np.random.randn(10000,100)+1j*np.random.randn(10000,100)
#         AT=A.T#.conj().copy()
# #        AT=A.T
#         # A=np.require(A,requirements='F_CONTIGUOUS')
#         # AT=np.require(AT,requirements='F_CONTIGUOUS')
#         # A=np.require(A,requirements='F')
#         # AT=np.require(AT,requirements='F')


#         T=ClassTimeIt.ClassTimeIt("doLMStep")
#         for i in range(20):
#             np.dot(AT,B)

#         T.timeit("%i"%i)

        
        if not(self.HasKernelMatrix):
            self.CalcKernelMatrix()
            self.SelectChannelKernelMat()
            T.timeit("CalcKernelMatrix")

        Ga=self.GiveSubVecGainAnt(Gains)

        f=(self.DicoData["flags_flat"]==0)
        # ind=np.where(f)[0]
        # if self.iAnt==56:
        #     print ind.size/float(f.size),np.abs(Gains[self.iAnt,0,0,0])

        if self.DataAllFlagged:
            return Ga.reshape((self.NDir,self.NJacobBlocks_X,self.NJacobBlocks_Y)),None,{"std":-1.,"max":-1.,"kapa":None}



        # if ind.size==0:
        #     return Ga.reshape((self.NDir,self.NJacobBlocks_X,self.NJacobBlocks_Y)),None,{"std":-1.,"max":-1.,"kapa":None}


        z=self.DicoData["data_flat"]#self.GiveDataVec()
        self.CalcJacobianAntenna(Gains)
        T.timeit("CalcJacobianAntenna")
        self.PrepareJHJ_LM()
        T.timeit("PrepareJHJ_L")



        T.timeit("GiveSubVecGainAnt")
        Jx=self.J_x(Ga)
        T.timeit("Jx")
        zr=z-Jx
        zr[self.DicoData["flags_flat"]]=0
        T.timeit("resid")

        # JH_z_0=np.load("LM.npz")["JH_z"]
        # x1_0=np.load("LM.npz")["x1"]
        # z_0=np.load("LM.npz")["z"]
        # Jx_0=np.load("LM.npz")["Jx"]




        InfoNoise={"std":np.std(zr[f]),"max":np.max(np.abs(zr[f])),"kapa":None}


        JH_z=self.JH_z(zr)
        T.timeit("JH_z")
        #self.JHJinv=ModLinAlg.invSVD(self.JHJ)
        #self.JHJinv=np.linalg.inv(self.JHJ)
        xi=Ga.flatten()
        T.timeit("self.JHJinv_x")
        

        if self.DoTikhonov:
            self.LambdaTkNorm
            Gi=xi.reshape((self.NDir,self.NJacobBlocks_X,self.NJacobBlocks_Y))
            JH_z=JH_z.reshape((self.NDir,self.NJacobBlocks_X,self.NJacobBlocks_Y))
            for polIndex in range(self.NJacobBlocks_X):
                gireg=Gi[:,polIndex,:]
                #gi=JH_z[:,polIndex,:]
                x0reg=self.X0[:,polIndex,:]
                Linv=(self.Linv[:,polIndex,:])
                JH_z[:,polIndex,:]-=self.LambdaTkNorm*Linv*(gireg-x0reg)
        dx = (1./(1.+self.LambdaLM)) * self.JHJinv_x(JH_z)

        
        
        
        # if self.iAnt==5:
        #     f=(self.DicoData["flags_flat"]==0)
        #     pylab.figure(2)
        #     pylab.clf()
        #     pylab.plot((z[f])[::1])#[::11])
        #     pylab.plot((Jx[f])[::1])#[::11])
        #     pylab.plot(zr[f][::1])#[::11])
        #     pylab.draw()
        #     pylab.show(False)
        #     pylab.pause(0.1)
        #     stop

        # # pylab.figure(2)
        # # pylab.clf()
        # # #pylab.plot((z)[::11])
        # # #pylab.plot((Jx-Jx_0)[::11])
        # # #pylab.plot(zr[::11])
        # # #pylab.plot(JH_z.flatten())
        # # #pylab.plot(JH_z_0.flatten())
        # # pylab.plot(x1.flatten())
        # # pylab.plot(x1_0.flatten())
        # # pylab.draw()
        # # pylab.show(False)
        # # pylab.pause(0.1)

        # stop
        # # np.savez("LM",JH_z=JH_z,x1=x1,z=z,Jx=Jx)
 
        # print JH_z.shape

        dx+=xi
        del(self.LJacob)
        T.timeit("rest")
        # print self.iAnt,np.mean(x1),x1.size,ind.size

        return dx.reshape((self.NDir,self.NJacobBlocks_X,self.NJacobBlocks_Y)),None,InfoNoise
