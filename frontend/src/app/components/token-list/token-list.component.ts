import { AfterViewInit, Component, OnDestroy, ViewChild } from '@angular/core';
import { MaterialDesignModule } from '../../modules/material-design/material-design.module';
import { CommonModule } from '@angular/common';
import { SeedTokenFactoryService } from '../../services/seed-token-factory.service';
import { Subscription } from 'rxjs';
import { MatTableDataSource } from '@angular/material/table';
import { MatSort } from '@angular/material/sort';
import { MatPaginator } from '@angular/material/paginator';
import { seedTokenAbi as abi } from '../../contracts/seed-token.abi';
import { ethers } from 'ethers';
import { MatDialog } from '@angular/material/dialog';
import { MintDialogComponent } from './mint-dialog/mint-dialog.component';
import { ProviderService } from '../../services/provider.service';
import { Clipboard } from '@angular/cdk/clipboard';
import { ChangeOwnerDialogComponent } from './change-owner-dialog/change-owner-dialog.component';
import { seedTokenFactoryAbi } from '../../contracts/seed-token-factory.abi';
 
export interface Token {
  index: number;
  address: string;
  name: string;
  symbol: string;
  supply: bigint;
  balance: bigint;
  owner: string;
  isOwner: boolean;
  contract: ethers.Contract;
}
 
@Component({
  selector: 'app-token-list',
  standalone: true,
  imports: [
    CommonModule,
    MaterialDesignModule
  ],
  templateUrl: './token-list.component.html',
  styleUrl: './token-list.component.css'
})
export class TokenListComponent implements AfterViewInit, OnDestroy {
  tokenColumns: string[] = [
    'symbol', 'supply', 'balance', 'mint', 'owner'
  ];
 
  @ViewChild('tokenSort') sort!: MatSort;
  @ViewChild('tokenPaginator') paginator!: MatPaginator;
 
  private changes: Subscription | null = null;
  private pendingFactories: any[] = [];
  private eventPollingTimer: ReturnType<typeof setTimeout> | null = null;
  private eventPollingFactory: any = null;
  private lastScannedBlock: number | null = null;
  private eventPollDelay = 15_000;
  private readonly maxRpcBlockSpan = 9_999;
 
  constructor(
    public seedTokenFactoryService: SeedTokenFactoryService,
    private providerService: ProviderService,
    private dialog: MatDialog,
    private clipboard: Clipboard
  ) {}
 
  private appendCreatedToken = async (event: any, factory: any) => {
    const tokenAddress = event.args[0];
    const owner = event.args[1];
 
    const tokenList = this.seedTokenFactoryService.tokenList.data;
    if (tokenList.some(token => token.address.toLowerCase() === tokenAddress.toLowerCase())) {
      return;
    }
 
    const signer: any = factory.runner;
    const signerAddress = signer?.address;
 
    const contract = new ethers.Contract(
      tokenAddress,
      abi,
      signer
    );
    const readContract = new ethers.Contract(
      tokenAddress,
      abi,
      this.providerService.getReadProvider()
    );
 
    const token: Token = await this.getToken(
      signerAddress,
      tokenList.length,
      tokenAddress,
      owner,
      contract,
      readContract
    );
 
    this.seedTokenFactoryService.tokenList.data = [...tokenList, token];
  };
 
  ngAfterViewInit(): void {
    this.changes = this.seedTokenFactoryService.changes.subscribe(
      (factory: any) => {
        this.pendingFactories.push(factory);
        if (this.pendingFactories.length == 1) {
          this.consumeAndUpdate();
        } //else another consumeAndUpdate() call is still running
 
      }
    );
  }
 
  consumeAndUpdate() {
    if (this.pendingFactories.length > 0) {
      //we only care about the last pending factory
      const length = this.pendingFactories.length;
      const lastFactory = this.pendingFactories[length - 1];
      this.stopEventPolling();
      this.updateTokenList(lastFactory).then(() => {
        //remove all pending factories up to the processed factory
        this.pendingFactories = this.pendingFactories.slice(length);
        //process newly added factories if any
        this.consumeAndUpdate();
      }).catch((error) => {
        this.pendingFactories = [];
        console.error('Could not load the token list. The wallet remains connected; retry after the RPC is available.', error);
      });
    }
  }
 
  async updateTokenList(factory: any) {
    const initialBlock = factory
      ? await this.providerService.getReadProvider().getBlockNumber()
      : null;
    if (factory && initialBlock == null) {
      throw new Error('Could not read the current block to monitor token creation events.');
    }

    const tokens: Token[] = [];
    this.paginator.length = tokens.length;
 
    this.seedTokenFactoryService.tokenList = new MatTableDataSource<Token>(tokens);
    this.seedTokenFactoryService.tokenList.sort = this.sort;
    this.seedTokenFactoryService.tokenList.paginator = this.paginator;
 
    this.seedTokenFactoryService.tokenCount = 0;
    this.seedTokenFactoryService.tokenIndex = 0;
 
    this.providerService.changes.next({});
 
    if (factory) {
      const signer = factory.runner;
      const signerAddress = signer?.address;
 
      const readProvider = this.providerService.getReadProvider();
      const readFactory = new ethers.Contract(
        await factory.getAddress(),
        seedTokenFactoryAbi,
        readProvider
      );
      const tokenCount = await readFactory.getNumberOfTokens();
      this.seedTokenFactoryService.tokenCount = tokenCount;
      for (let i = 0; i < tokenCount; i++) {
        this.seedTokenFactoryService.tokenIndex = i;
        const address = await readFactory.tokens(i);
        const contract = new ethers.Contract(
          address,
          abi,
          signer
        );
        const readContract = new ethers.Contract(address, abi, readProvider);
 
        const owner = await readContract.owner();
 
        const token: Token = await this.getToken(
          signerAddress,
          i,
          address,
          owner,
          contract,
          readContract
        );
 
        tokens.push(token);
 
        this.seedTokenFactoryService.tokenList.data = tokens;
      }
      this.seedTokenFactoryService.tokenIndex = tokenCount;
      this.providerService.changes.next({});
      this.startEventPolling(factory, initialBlock!);
    }
  }

  private startEventPolling(factory: any, initialBlock: number): void {
    this.stopEventPolling();
    this.eventPollingFactory = factory;
    this.lastScannedBlock = initialBlock;
    this.eventPollDelay = 15_000;
    this.scheduleEventPoll(factory, this.eventPollDelay);
  }

  private scheduleEventPoll(factory: any, delay: number): void {
    this.eventPollingTimer = setTimeout(() => {
      void this.pollForCreatedTokens(factory);
    }, delay);
  }

  private async pollForCreatedTokens(factory: any): Promise<void> {
    if (factory !== this.eventPollingFactory || this.lastScannedBlock == null) return;

    try {
      const provider = this.providerService.getReadProvider();
      const reader = new ethers.Contract(
        await factory.getAddress(),
        seedTokenFactoryAbi,
        provider
      );

      const latestBlock = await provider.getBlockNumber();
      const fromBlock = this.lastScannedBlock + 1;
      const toBlock = Math.min(latestBlock, fromBlock + this.maxRpcBlockSpan);
      if (fromBlock <= toBlock) {
        const filter = reader.filters.SeedTokenCreation(null, null, null, null);
        const events = await reader.queryFilter(filter, fromBlock, toBlock);
        if (factory !== this.eventPollingFactory) return;

        for (const event of events) {
          await this.appendCreatedToken(event, factory);
        }
        this.lastScannedBlock = toBlock;
      }

      this.eventPollDelay = 15_000;
    } catch (error) {
      this.eventPollDelay = Math.min(this.eventPollDelay * 2, 120_000);
      console.warn(`Token event poll failed; retrying in ${this.eventPollDelay / 1000}s.`, error);
    }

    if (factory === this.eventPollingFactory) {
      this.scheduleEventPoll(factory, this.eventPollDelay);
    }
  }

  private stopEventPolling(): void {
    if (this.eventPollingTimer) clearTimeout(this.eventPollingTimer);
    this.eventPollingTimer = null;
    this.eventPollingFactory = null;
    this.lastScannedBlock = null;
  }
 
  private async getToken(
    signerAddress: string,
    index: number,
    tokenAddress: string,
    owner: string,
    contract: ethers.Contract,
    readContract: ethers.Contract = contract
  ): Promise<Token> {
    const decimals = await readContract.decimals();
    const divisor = 10n ** decimals;
    const balance = signerAddress
                  ? (await readContract.balanceOf(signerAddress)) / divisor
                  : 0n;
 
    return {
      index: index,
      address: tokenAddress,
      name: await readContract.name(),
      symbol: await readContract.symbol(),
      supply: (await readContract.totalSupply()) / divisor,
      balance: balance,
      owner: owner,
      isOwner: (signerAddress?.toLowerCase() === owner?.toLowerCase()),
      contract: contract
    };
  }
 
  ngOnDestroy(): void {
    this.changes?.unsubscribe();
    this.stopEventPolling();
  }
 
  copyToClipboard(value: string) {
    this.clipboard.copy(value);
  }
 
  openMintDialog(element: Token) {
    this.dialog.open(MintDialogComponent, {
      width: 'min(31rem, calc(100vw - 2rem))',
      maxWidth: '31rem',
      data: {
        address: element.address,
        name: element.name,
        symbol: element.symbol,
        amount: '',
        contract: element.contract,
        onMint: async () => {
          await this.updateToken(element);
        }
      }
    });
  }
 
  openChangeOwnerDialog(element: Token) {
    this.dialog.open(ChangeOwnerDialogComponent, {
      width: 'min(31rem, calc(100vw - 2rem))',
      maxWidth: '31rem',
      data: {
        address: element.address,
        name: element.name,
        symbol: element.symbol,
        newOwnerAddress: '',
        contract: element.contract,
        onChangeOwner: async () => {
          await this.updateToken(element);
        }
      }
    });
  }
 
  async updateToken(element: Token) {
    const signerAddress = this.providerService.getAddress();
    const contract = element.contract;
    const decimals = await contract.decimals();
    const divisor = 10n ** decimals;
 
    const supply = (await contract.totalSupply()) / divisor;
    const balance = (await contract.balanceOf(signerAddress)) / divisor;
    const owner = await contract.owner();
    const isOwner = (signerAddress?.toLowerCase() === owner?.toLowerCase());
 
    const tokenList = this.seedTokenFactoryService.tokenList.data;
    const token = tokenList[element.index];
    token.supply = supply;
    token.balance = balance;
    token.owner = owner;
    token.isOwner = isOwner;
 
    this.providerService.changes.next({});
  }
}
