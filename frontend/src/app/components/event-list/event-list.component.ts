import { AfterViewInit, Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MaterialDesignModule } from '../../modules/material-design/material-design.module';
import { SeedTokenFactoryService } from '../../services/seed-token-factory.service';
import { ethers } from 'ethers';
import { MatSort } from '@angular/material/sort';
import { MatPaginator } from '@angular/material/paginator';
import { MatTableDataSource } from '@angular/material/table';
import { Subscription } from 'rxjs';
import { CommonModule } from '@angular/common';
 
@Component({
  selector: 'app-event-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MaterialDesignModule
  ],
  templateUrl: './event-list.component.html',
  styleUrl: './event-list.component.css'
})
export class EventListComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly defaultHistoryBlocks = 100_000;
  private readonly maxHistoryBlocks = 100_000;
  private readonly maxRpcBlockSpan = 9_999;
  private searchVersion = 0;

  from: string = '';
  to: string = '';
  owner: string = '';
  name: string = '';
  symbol: string = '';
  isLoading = false;
  errorMessage = '';
 
  eventColumns: string[] = [
    'blockNumber', 'tokenAddress', 'owner'
  ];
 
  @ViewChild('eventSort') sort!: MatSort;
  @ViewChild('eventPaginator') paginator!: MatPaginator;
 
  eventList = new MatTableDataSource<ethers.EventLog>([]);
  isShowEvents = true;
 
  private changes: Subscription | null = null;
 
  constructor(
    private seedTokenFactoryService: SeedTokenFactoryService
  ) {}
 
  ngOnInit(): void {
    this.changes = this.seedTokenFactoryService.changes.subscribe(
      (factory: ethers.BaseContract | null) => {
        this.isShowEvents = (factory != null);
        if (this.isShowEvents) {
          void this.searchEvents();
        }
      }
    );
  }
 
  ngOnDestroy(): void {
    this.changes?.unsubscribe();
  }

  ngAfterViewInit(): void {
    this.eventList.sort = this.sort;
    this.eventList.paginator = this.paginator;
  }
 
  async searchEvents() {
    const searchVersion = ++this.searchVersion;
    const contract = this.seedTokenFactoryService.get();
    if (!contract) return;

    this.isLoading = true;
    this.errorMessage = '';
    try {
      const latestBlock = await contract.runner?.provider?.getBlockNumber();
      if (latestBlock == null) {
        throw new Error('Could not read the current Sepolia block. Check the RPC connection and CORS settings.');
      }

      const to = this.parseBlock(this.to, latestBlock, 'To');
      const defaultFrom = Math.max(0, to - this.defaultHistoryBlocks + 1);
      const from = this.parseBlock(this.from, defaultFrom, 'From');
      if (from > to) {
        throw new Error('From block must be less than or equal to To block.');
      }
      if (to - from + 1 > this.maxHistoryBlocks) {
        throw new Error(`Choose a range of ${this.maxHistoryBlocks.toLocaleString()} blocks or fewer.`);
      }

      // Show the effective defaults so users can see exactly which range is queried.
      this.from = String(from);
      this.to = String(to);

      const filter = contract.filters.SeedTokenCreation(
        null,
        this.splitAddress(this.owner),
        this.split(this.name),
        this.split(this.symbol)
      );
      const events: ethers.EventLog[] = [];
      for (let chunkFrom = from; chunkFrom <= to; chunkFrom += this.maxRpcBlockSpan + 1) {
        const chunkTo = Math.min(to, chunkFrom + this.maxRpcBlockSpan);
        events.push(...await contract.queryFilter(filter, chunkFrom, chunkTo));
      }

      if (searchVersion !== this.searchVersion) return;
      this.eventList = new MatTableDataSource<ethers.EventLog>(events);
      if (this.sort) this.eventList.sort = this.sort;
      if (this.paginator) {
        this.paginator.length = events.length;
        this.eventList.paginator = this.paginator;
      }
    } catch (error) {
      if (searchVersion !== this.searchVersion) return;
      this.eventList = new MatTableDataSource<ethers.EventLog>([]);
      this.errorMessage = error instanceof Error ? error.message : 'Could not load creation events.';
    } finally {
      if (searchVersion === this.searchVersion) this.isLoading = false;
    }
  }

  private parseBlock(value: string, fallback: number, label: string): number {
    if (!value.trim()) return fallback;
    if (!/^\d+$/.test(value.trim())) {
      throw new Error(`${label} block must be a whole number.`);
    }
    const block = Number(value);
    if (!Number.isSafeInteger(block) || block < 0) {
      throw new Error(`${label} block must be a valid non-negative block number.`);
    }
    return block;
  }
 
  private split(values: string): string[] | null {
    if (!values) {
      return null;
    }
    const split = values.split(',').map(value => value.trim()).filter(Boolean);
    return split.length ? split : null;
  }
 
  private splitAddress(values: string): string[] | null {
    if (!values) {
      return null;
    }
    const split: string[] = [];
    values.split(',').forEach((value: string) => {
      const address = value.trim();
      if (ethers.isAddress(address)) {
        split.push(address);
      } else if (address) {
        throw new Error(`'${address}' is not a valid owner address.`);
      }
    });
    return split.length ? split : null;
  }
}
